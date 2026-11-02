import json
import logging
from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields, http
from odoo.exceptions import AccessDenied
from odoo.http import Response, request
from odoo.tools import mute_logger

from ..models.bus_incident import KINDS as INCIDENT_KINDS
from ..models.utils import parse_traccar_dt, tile_url
from .portal import RateLimiter

_logger = logging.getLogger(__name__)

LOGIN_LIMIT = 10          # attempts per IP and per login, per minute and worker process
login_limiter = RateLimiter(LOGIN_LIMIT, 60.0)
INCIDENT_KIND = {key for key, _label in INCIDENT_KINDS}


def json_response(data, status=200):
    return Response(json.dumps(data), status=status, content_type='application/json',
                    headers=[('Cache-Control', 'no-store')])


def bearer_token():
    header = request.httprequest.headers.get('Authorization', '')
    return header[7:].strip() if header.startswith('Bearer ') else ''


def read_body():
    """The JSON object sent by the app, or None when the body is not one."""
    try:
        body = json.loads(request.httprequest.get_data(as_text=True) or '{}')
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def as_int(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def utc_z(value):
    return value.isoformat() + 'Z' if value else None


class BusDriverApi(http.Controller):
    """JSON API for the driver tablet app. It authenticates with its own bearer token
    (Odoo 16 only accepts API keys on its RPC endpoints, not on controllers)."""

    def _driver(self):
        return request.env['bus.driver.token']._user_for(bearer_token())

    def _auth(self):
        user = self._driver()
        if not user:
            return None, json_response({'error': 'unauthorized'}, 401)
        return user, None

    def _active_shift(self, user):
        return request.env['bus.shift'].with_user(user).search([('state', '=', 'active')], limit=1)

    def _shift_payload(self, shift):
        return {
            'id': shift.id,
            'vehicle_id': shift.vehicle_id.id,
            'route_id': shift.route_id.id,
            'start': utc_z(shift.start),
        }

    @http.route('/bus_tracking/driver/login', type='http', auth='public', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        body = read_body()
        if body is None:
            return json_response({'error': 'bad_request'}, 400)
        login, password = body.get('login'), body.get('password')
        if not (isinstance(login, str) and isinstance(password, str) and login and password):
            return json_response({'error': 'bad_request'}, 400)
        ip = request.httprequest.remote_addr
        if not (login_limiter.allow('ip:%s' % ip) and login_limiter.allow('login:%s' % login.lower())):
            return Response(status=429, headers=[('Retry-After', '60')])
        try:
            uid = request.env['res.users'].authenticate(
                request.db, login, password, {'interactive': False, 'remote_addr': ip})
        except AccessDenied:
            uid = False
        user = request.env['res.users'].sudo().browse(uid) if uid else request.env['res.users']
        # One answer for a wrong password and for a user without the driver role.
        if not user or not user.has_group('bus_tracking.group_bus_driver'):
            return json_response({'error': 'invalid_credentials'}, 401)
        label = body.get('device') if isinstance(body.get('device'), str) else ''
        token = request.env['bus.driver.token']._issue(user, label)
        return json_response({'token': token, 'driver': {'id': user.id, 'name': user.name}})

    @http.route('/bus_tracking/driver/login_badge', type='http', auth='public', methods=['POST'], csrf=False)
    def login_badge(self, **kwargs):
        body = read_body()
        if body is None:
            return json_response({'error': 'bad_request'}, 400)
        raw_token = body.get('badge_token') or body.get('token')
        if not (isinstance(raw_token, str) and raw_token):
            return json_response({'error': 'bad_request'}, 400)
        ip = request.httprequest.remote_addr
        if not login_limiter.allow('ip:%s' % ip):
            return Response(status=429, headers=[('Retry-After', '60')])
        # Only a badge buys a session here: accepting a session token too would let a stolen one
        # be renewed for ever.
        user = request.env['bus.driver.token']._user_for_badge(raw_token)
        if not user:
            return json_response({'error': 'invalid_badge'}, 401)
        label = body.get('device') if isinstance(body.get('device'), str) else 'tablet_badge'
        token = request.env['bus.driver.token']._issue(user, label)
        return json_response({'token': token, 'driver': {'id': user.id, 'name': user.name}})

    @http.route('/bus_tracking/driver/logout', type='http', auth='public', methods=['POST'], csrf=False)
    def logout(self, **kwargs):
        token = bearer_token()
        if token:
            request.env['bus.driver.token']._revoke(token)
        return json_response({'ok': True})

    @http.route('/bus_tracking/driver/me', type='http', auth='public', methods=['POST'], csrf=False)
    def me(self, **kwargs):
        user, err = self._auth()
        if err:
            return err
        env = request.env(user=user.id)
        busy = {s.vehicle_id.id: s.user_id.id for s in env['bus.shift'].sudo().search([('state', '=', 'active')])}
        shift = env['bus.shift'].search([('state', '=', 'active')], limit=1)
        return json_response({
            'driver': {'id': user.id, 'name': user.name},
            'vehicles': [{
                'id': bus.id,
                'name': bus.name,
                'plate': bus.plate or '',
                'route_id': bus.route_id.id or None,
                'available': busy.get(bus.id, user.id) == user.id,
                # A bus without a GPS device in Traccar cannot start a shift (no_gps).
                'has_gps': bool(bus.sudo().traccar_unique_id),
            } for bus in env['bus.vehicle'].search([])],
            'routes': [{
                'id': route.id,
                'code': route.code,
                'name': route.name,
                'color': route.color or '#3388ff',
            } for route in env['bus.route'].search([])],
            'shift': self._shift_payload(shift) if shift else None,
        })

    @http.route('/bus_tracking/driver/shift/start', type='http', auth='public', methods=['POST'], csrf=False)
    def shift_start(self, **kwargs):
        user, err = self._auth()
        if err:
            return err
        body = read_body()
        if body is None:
            return json_response({'error': 'bad_request'}, 400)
        vehicle_id, route_id = as_int(body.get('vehicle_id')), as_int(body.get('route_id'))
        if not (vehicle_id and route_id):
            return json_response({'error': 'bad_request'}, 400)
        env = request.env(user=user.id)
        bus = env['bus.vehicle'].browse(vehicle_id)
        route = env['bus.route'].browse(route_id)
        # Archived buses and routes are kept for history only.
        if not bus.exists() or not route.exists() or not bus.active or not route.active:
            return json_response({'error': 'bad_request'}, 400)
        unique_id = bus.sudo().traccar_unique_id
        if not unique_id:
            return json_response({'error': 'no_gps'}, 409)
        # Without it the tablet has nowhere to send positions: better refuse than a silent shift.
        gps_url = (env['ir.config_parameter'].sudo().get_param('bus_tracking.gps_url') or '').strip().rstrip('/')
        if not gps_url:
            return json_response({'error': 'no_gps_url'}, 409)
        Shift = env['bus.shift'].sudo()
        with mute_logger('odoo.sql_db'):
            try:
                with env.cr.savepoint():
                    shift = Shift.create({
                        'user_id': user.id, 'vehicle_id': bus.id, 'route_id': route.id})
            except IntegrityError:
                return json_response({'error': 'conflict'}, 409)
        shift._assign_vehicle()
        return json_response({
            'shift': self._shift_payload(shift),
            'traccar_unique_id': unique_id,
            'gps_url': gps_url,
        })

    @http.route('/bus_tracking/driver/shift/end', type='http', auth='public', methods=['POST'], csrf=False)
    def shift_end(self, **kwargs):
        user, err = self._auth()
        if err:
            return err
        shift = self._active_shift(user)
        if not shift:
            return json_response({'error': 'no_shift'}, 409)
        shift.sudo()._end()
        return json_response({'ok': True})

    @http.route('/bus_tracking/driver/state', type='http', auth='public', methods=['POST'], csrf=False)
    def state(self, **kwargs):
        user, err = self._auth()
        if err:
            return err
        shift = self._active_shift(user)
        if not shift:
            return json_response({'error': 'no_shift'}, 409)
        bus = shift.vehicle_id.sudo()
        trip = shift._trip_progress()
        arrived = trip['arrived']
        since = fields.Datetime.now() - timedelta(hours=2)
        alerts = request.env['bus.alert'].sudo().search([
            ('vehicle_id', '=', bus.id),
            '|', ('state', '=', 'open'), ('start_time', '>=', since),
        ])
        sos = request.env['bus.incident'].sudo().search(
            [('shift_id', '=', shift.id), ('kind', '=', 'sos')], order='create_date desc', limit=1)
        return json_response({
            'shift': self._shift_payload(shift),
            # The last SOS of this shift and whether someone in the office saw it.
            'sos': {
                'id': sos.id,
                'sent_at': utc_z(sos.reported_at or sos.create_date),
                'seen_at': utc_z(sos.acknowledged_at),
                'seen_by': sos.acknowledged_by.name or None,
            } if sos else None,
            'current_stop_id': bus.current_stop_id.id or None,
            'next_stop_id': trip['next_stop'].id or None,
            # 'back' once the bus reached the last stop: the stops come in the order it travels them.
            'direction': trip['direction'],
            'stops': [{
                'id': stop.id,
                'name': stop.name,
                'sequence': stop.sequence,
                'arrived_at': utc_z(arrived.get(stop.id)),
            } for stop in trip['stops']],
            'alerts': [{
                'id': alert.id,
                'kind': alert.kind,
                'state': alert.state,
                'detail': alert.with_context(lang=user.lang).detail or '',
                'start': utc_z(alert.start_time),
            } for alert in alerts],
        })

    @http.route('/bus_tracking/driver/route', type='http', auth='public', methods=['POST'], csrf=False)
    def route(self, **kwargs):
        user, err = self._auth()
        if err:
            return err
        shift = self._active_shift(user)
        if not shift:
            return json_response({'error': 'no_shift'}, 409)
        route = shift.route_id.sudo()
        return json_response({
            'id': route.id,
            'code': route.code,
            'name': route.name,
            'color': route.color or '#3388ff',
            'stops': [{
                'id': stop.id,
                'name': stop.name,
                'sequence': stop.sequence,
                'lat': stop.latitude,
                'lon': stop.longitude,
                'radius': stop.radius,
            } for stop in route.stop_ids],
            'lines': route._map_lines(),
            'tile_url': tile_url(request.env),
        })

    @http.route('/bus_tracking/driver/incident', type='http', auth='public', methods=['POST'], csrf=False)
    def incident(self, **kwargs):
        user, err = self._auth()
        if err:
            return err
        shift = self._active_shift(user)
        if not shift:
            return json_response({'error': 'no_shift'}, 409)
        body = read_body()
        if body is None:
            return json_response({'error': 'bad_request'}, 400)
        kind = body.get('kind')
        if kind not in INCIDENT_KIND:
            return json_response({'error': 'bad_request'}, 400)
        note = body.get('note')
        if note is None:
            note = ''
        if not isinstance(note, str) or len(note) > 300:
            return json_response({'error': 'bad_request'}, 400)
        lat, lon = body.get('lat', None), body.get('lon', None)
        if lat is not None or lon is not None:
            if isinstance(lat, bool) or isinstance(lon, bool):
                return json_response({'error': 'bad_request'}, 400)
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                return json_response({'error': 'bad_request'}, 400)
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return json_response({'error': 'bad_request'}, 400)
        else:
            lat = lon = False
        # The tablet sends when the driver pressed the button; it is kept only when it falls
        # inside this shift and not in the future, so a wrong tablet clock cannot reorder things.
        now = fields.Datetime.now()
        reported_at = parse_traccar_dt(body.get('reported_at'))
        if not reported_at or not (shift.start - timedelta(minutes=1) <= reported_at <= now + timedelta(minutes=1)):
            reported_at = now
        incident = request.env['bus.incident'].sudo().create({
            'reported_at': min(reported_at, now),
            'shift_id': shift.id,
            'vehicle_id': shift.vehicle_id.id,
            'kind': kind,
            'note': note or False,
            'latitude': lat,
            'longitude': lon,
        })
        return json_response({'id': incident.id})
