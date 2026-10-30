import json
import logging

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import Response, request

from .portal import RateLimiter

_logger = logging.getLogger(__name__)

LOGIN_LIMIT = 10          # attempts per IP and per login, per minute and worker process
login_limiter = RateLimiter(LOGIN_LIMIT, 60.0)


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


class BusDriverApi(http.Controller):
    """JSON API for the driver tablet app. It authenticates with its own bearer token
    (Odoo 16 only accepts API keys on its RPC endpoints, not on controllers)."""

    def _driver(self):
        return request.env['bus.driver.token']._user_for(bearer_token())

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

    @http.route('/bus_tracking/driver/logout', type='http', auth='public', methods=['POST'], csrf=False)
    def logout(self, **kwargs):
        token = bearer_token()
        if token:
            request.env['bus.driver.token']._revoke(token)
        return json_response({'ok': True})

    @http.route('/bus_tracking/driver/me', type='http', auth='public', methods=['POST'], csrf=False)
    def me(self, **kwargs):
        user = self._driver()
        if not user:
            return json_response({'error': 'unauthorized'}, 401)
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
            } for bus in env['bus.vehicle'].search([])],
            'routes': [{
                'id': route.id,
                'code': route.code,
                'name': route.name,
                'color': route.color or '#3388ff',
            } for route in env['bus.route'].search([])],
            'shift': {
                'id': shift.id,
                'vehicle_id': shift.vehicle_id.id,
                'route_id': shift.route_id.id,
                'start': shift.start.isoformat() + 'Z',
            } if shift else None,
        })
