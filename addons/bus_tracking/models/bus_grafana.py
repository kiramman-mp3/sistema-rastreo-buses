"""The way into the Grafana dashboards, from inside Odoo.

Odoo is the only door: a person who is signed in to Odoo and belongs to the bus users gets a token signed with a secret
that Odoo and Grafana share (HS256, the `auth.jwt` login of Grafana). The token says who it is for (`odoo-<id>`, no
name), that the role is always Viewer, and when it stops working. The secret never leaves the server.
"""
import base64
import hashlib
import hmac
import json
import os
import time

from odoo import _, api, models
from odoo.exceptions import AccessError

ISSUER = 'odoo-bus-tracking'
KEY_ID = 'odoo'
# One working day. Grafana sends the token with every query it makes, so it has to outlive the screen that is open.
DEFAULT_MINUTES = 480
MIN_MINUTES, MAX_MINUTES = 5, 1440
MIN_SECRET = 16
# uid in Grafana, title on screen (the same uids as bi/grafana/dashboards/*.json)
DASHBOARDS = [
    ('bus-resumen', "Summary"),
    ('bus-rutas', "Lines"),
    ('bus-puntualidad', "Punctuality"),
    ('bus-recorridos', "Trips"),
    ('bus-incidencias', "Incidents"),
    ('bus-calidad', "System quality"),
]


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def sign(claims, secret):
    """A JSON Web Token (HS256) with the claims."""
    head = _b64(json.dumps({'alg': 'HS256', 'typ': 'JWT', 'kid': KEY_ID}, separators=(',', ':')).encode())
    body = _b64(json.dumps(claims, separators=(',', ':')).encode())
    signature = hmac.new(secret.encode(), ('%s.%s' % (head, body)).encode(), hashlib.sha256).digest()
    return '%s.%s.%s' % (head, body, _b64(signature))


class BusGrafana(models.AbstractModel):
    _name = 'bus.grafana'
    _description = 'Access to the Grafana dashboards'

    @api.model
    def _settings(self):
        """(address, secret, minutes the token lasts). The system parameters win over the environment."""
        params = self.env['ir.config_parameter'].sudo()
        url = (params.get_param('bus_tracking.grafana_url') or os.environ.get('GRAFANA_URL') or '').strip().rstrip('/')
        secret = params.get_param('bus_tracking.grafana_jwt_secret') or os.environ.get('GRAFANA_JWT_SECRET') or ''
        try:
            minutes = int(params.get_param('bus_tracking.grafana_token_minutes') or DEFAULT_MINUTES)
        except ValueError:
            minutes = DEFAULT_MINUTES
        return url, secret, min(max(minutes, MIN_MINUTES), MAX_MINUTES)

    @api.model
    def access(self):
        """What the screen needs to open Grafana: its address and a token for the user, or why it cannot."""
        user = self.env.user
        if not user.has_group('bus_tracking.group_bus_user'):
            raise AccessError(_("Bus tracking access required."))
        url, secret, minutes = self._settings()
        can_manage = user.has_group('bus_tracking.group_bus_manager')
        if not url or len(secret) < MIN_SECRET:
            return {'configured': False, 'can_manage': can_manage}
        now = int(time.time())
        claims = {'iss': ISSUER, 'sub': 'odoo-%s' % user.id, 'role': 'Viewer', 'iat': now, 'nbf': now - 5,
                  'exp': now + minutes * 60}
        return {
            'configured': True, 'can_manage': can_manage, 'url': url, 'token': sign(claims, secret),
            'expires_in': minutes * 60,
            'dashboards': [{'uid': uid, 'title': _(title)} for uid, title in DASHBOARDS],
        }
