import os

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import Response, request

from ..models.bus_push import endpoint_allowed

SERVICE_WORKER = os.path.join(os.path.dirname(__file__), os.pardir, 'static', 'src', 'push', 'sw.js')


class BusPush(http.Controller):
    """Registration of browsers for push notifications. Managers only: they are the only people
    who receive notifications."""

    @staticmethod
    def _require_manager():
        if not request.env.user.has_group('bus_tracking.group_bus_manager'):
            raise AccessError(_("Only managers can receive notifications."))

    @staticmethod
    def _subscriptions():
        return request.env['bus.push.subscription'].sudo()

    @http.route('/bus_tracking/sw.js', type='http', auth='public', methods=['GET'])
    def service_worker(self):
        with open(SERVICE_WORKER, encoding='utf-8') as handle:
            body = handle.read()
        return Response(body, content_type='application/javascript; charset=utf-8',
                        headers=[('Cache-Control', 'no-cache')])

    @http.route('/bus_tracking/push/state', type='json', auth='user')
    def state(self, endpoint=None):
        self._require_manager()
        subscriptions = self._subscriptions()
        available = subscriptions._available()
        mine = [('user_id', '=', request.env.uid)]
        return {
            'available': available,
            'key': subscriptions._vapid()[1] if available else '',
            'subscribed': bool(endpoint) and bool(subscriptions.search_count(mine + [('endpoint', '=', endpoint)])),
            'devices': subscriptions.search_count(mine),
        }

    @http.route('/bus_tracking/push/subscribe', type='json', auth='user')
    def subscribe(self, endpoint=None, keys=None, user_agent=''):
        self._require_manager()
        keys = keys if isinstance(keys, dict) else {}
        p256dh, auth = keys.get('p256dh'), keys.get('auth')
        if not endpoint_allowed(endpoint):
            return {'ok': False, 'error': 'endpoint'}
        if not (isinstance(p256dh, str) and isinstance(auth, str) and 0 < len(p256dh) < 200 and 0 < len(auth) < 100):
            return {'ok': False, 'error': 'keys'}
        values = {
            'user_id': request.env.uid,
            'endpoint': endpoint,
            'p256dh': p256dh,
            'auth': auth,
            'user_agent': str(user_agent or request.httprequest.user_agent.string)[:250],
        }
        existing = self._subscriptions().search([('endpoint', '=', endpoint)])
        if existing:
            existing.write(values)
        else:
            self._subscriptions().create(values)
        return {'ok': True}

    @http.route('/bus_tracking/push/unsubscribe', type='json', auth='user')
    def unsubscribe(self, endpoint=None):
        self._require_manager()
        self._subscriptions().search([('user_id', '=', request.env.uid), ('endpoint', '=', endpoint)]).unlink()
        return {'ok': True}

    @http.route('/bus_tracking/push/test', type='json', auth='user')
    def test(self):
        self._require_manager()
        sent = self._subscriptions()._send_to_user(request.env.user, {
            'title': _("Test notification"),
            'body': _("If you can read this, notifications reach this device."),
            'url': '/web#action=bus_tracking.action_bus_alert',
            'tag': 'bus-tracking-test',
        })
        return {'sent': sent}
