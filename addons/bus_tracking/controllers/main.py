import hmac
import json
import logging
from datetime import timedelta

from odoo import fields, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import Response, request

from ..models.utils import map_center

_logger = logging.getLogger(__name__)


class BusTrackingController(http.Controller):

    def _check_user(self):
        if not request.env.user.has_group('bus_tracking.group_bus_user'):
            raise AccessError("Bus tracking access required.")

    @http.route('/bus_tracking/live', type='json', auth='user')
    def live(self):
        self._check_user()
        env = request.env
        alerts = {}
        for alert in env['bus.alert'].search([('state', '=', 'open')]):
            alerts.setdefault(alert.vehicle_id.id, []).append(alert.kind)
        alert_labels = dict(env['bus.alert']._fields['kind']._description_selection(env))
        vehicles = []
        for bus in env['bus.vehicle'].search([('last_fix_time', '!=', False)]):
            vehicles.append({
                'id': bus.id,
                'name': bus.name,
                'plate': bus.plate or '',
                'driver': bus.driver_id.name or '',
                'route_id': bus.route_id.id,
                'route_name': bus.route_id.name or '',
                'color': bus.route_id.color or '#3388ff',
                'lat': bus.last_latitude,
                'lon': bus.last_longitude,
                'speed': round(bus.last_speed, 1),
                'course': bus.last_course,
                'fix_time': fields.Datetime.to_string(bus.last_fix_time),
                'status': bus.status,
                'connected': bus.connected,
                'stop': bus.current_stop_id.name or '',
                'alerts': alerts.get(bus.id, []),
            })
        routes = [{
            'id': r.id,
            'name': r.name,
            'code': r.code,
            'color': r.color or '#3388ff',
            'paths': r._map_lines(),
            'stops': [{
                'name': s.name,
                'lat': s.latitude,
                'lon': s.longitude,
                'radius': s.radius,
            } for s in r.stop_ids],
        } for r in env['bus.route'].search([])]
        return {'vehicles': vehicles, 'routes': routes, 'alert_labels': alert_labels,
                'map_center': list(map_center(env))}

    @http.route('/bus_tracking/track', type='json', auth='user')
    def track(self, vehicle_id, hours=4):
        self._check_user()
        since = fields.Datetime.now() - timedelta(hours=hours)
        positions = request.env['bus.position'].search([
            ('vehicle_id', '=', int(vehicle_id)),
            ('fix_time', '>=', since),
        ], order='fix_time asc')
        return [[p.latitude, p.longitude] for p in positions]

    @http.route('/bus_tracking/traccar/webhook', type='http', auth='public',
                methods=['POST'], csrf=False)
    def traccar_webhook(self, secret=None, **kwargs):
        env = request.env(su=True)
        expected = env['ir.config_parameter'].get_param('bus_tracking.webhook_secret')
        # The header keeps the secret out of access logs; the query parameter is kept for older setups.
        headers = request.httprequest.headers
        secret = secret or headers.get('X-Webhook-Secret') or headers.get('Authorization', '').removeprefix('Bearer ')
        if not expected or not secret or not hmac.compare_digest(
                expected.encode(), secret.encode()):
            return Response(status=403)
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True))
        except ValueError:
            return Response(status=400)
        if isinstance(payload, dict):
            try:
                env['bus.vehicle']._process_traccar_payload(payload)
            except (ValueError, ValidationError):
                return Response(status=400)
        return Response(status=200)

    @http.route('/bus_tracking/health', type='http', auth='public', methods=['GET'], csrf=False)
    def health(self, **kwargs):
        """Uptime-monitor endpoint: 200 while positions keep arriving, 503 once they go stale."""
        env = request.env(su=True)
        stale_minutes = int(env['ir.config_parameter'].get_param('bus_tracking.stale_minutes') or 10)
        status, code = 'ok', 200
        if stale_minutes > 0 and env['bus.vehicle'].search_count([('traccar_device_id', '!=', False)]):
            last = env['bus.vehicle'].search([('last_fix_time', '!=', False)], order='last_fix_time desc', limit=1)
            if not last or fields.Datetime.now() - last.last_fix_time > timedelta(minutes=stale_minutes):
                status, code = 'stale', 503
        return Response(json.dumps({'status': status}), status=code, content_type='application/json')
