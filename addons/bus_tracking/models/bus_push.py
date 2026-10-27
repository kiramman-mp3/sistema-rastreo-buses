import base64
import json
import logging
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Browsers hand out an endpoint on their vendor's push service. The server will POST to it, so only
# those services are accepted: otherwise a registered "endpoint" could point at an internal address.
ALLOWED_PUSH_HOSTS = (
    'fcm.googleapis.com',
    'android.googleapis.com',
    'push.services.mozilla.com',
    'push.apple.com',
    'notify.windows.com',
)


def endpoint_allowed(url):
    try:
        parsed = urlparse(url or '')
        host = (parsed.hostname or '').lower()
        port = parsed.port
    except ValueError:
        return False
    return (parsed.scheme == 'https' and port in (None, 443) and not parsed.username
            and any(host == allowed or host.endswith('.' + allowed) for allowed in ALLOWED_PUSH_HOSTS))


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


class BusPushSubscription(models.Model):
    _name = 'bus.push.subscription'
    _description = 'Browser Push Subscription'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    endpoint = fields.Char(required=True)
    p256dh = fields.Char(required=True)
    auth = fields.Char(required=True)
    user_agent = fields.Char()

    _sql_constraints = [
        ('endpoint_uniq', 'unique(endpoint)', "This device is already subscribed."),
    ]

    @api.model
    def _available(self):
        try:
            import pywebpush  # noqa: F401
        except ImportError:
            return False
        return True

    @api.model
    def _vapid(self):
        """(private PEM, public key for the browser). Created on first use and kept in system parameters."""
        icp = self.env['ir.config_parameter'].sudo()
        private = icp.get_param('bus_tracking.vapid_private')
        public = icp.get_param('bus_tracking.vapid_public')
        if not (private and public):
            key = ec.generate_private_key(ec.SECP256R1())
            private = key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()).decode()
            public = b64url(key.public_key().public_bytes(
                serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
            icp.set_param('bus_tracking.vapid_private', private)
            icp.set_param('bus_tracking.vapid_public', public)
        return private, public

    @api.model
    def _claim_subject(self):
        address = (self.env.company.email or '').strip() or 'noreply@localhost'
        return 'mailto:' + address

    def _send_one(self, payload):
        """Send one notification. Returns True when the push service accepted it."""
        self.ensure_one()
        from pywebpush import Vapid, WebPushException, webpush
        private, _public = self._vapid()
        try:
            webpush(
                subscription_info={'endpoint': self.endpoint, 'keys': {'p256dh': self.p256dh, 'auth': self.auth}},
                data=json.dumps(payload),
                vapid_private_key=Vapid.from_pem(private.encode()),
                vapid_claims={'sub': self._claim_subject()},
                ttl=3600,
                timeout=10,
            )
            return True
        except WebPushException as error:
            status = getattr(error.response, 'status_code', None)
            if status in (404, 410):          # the browser revoked or lost the subscription
                self.unlink()
            else:
                _logger.warning("Push to subscription %s failed: %s", self.id, error)
            return False

    @api.model
    def _send_to_user(self, user, payload):
        """Push to every device of the user. Returns how many were accepted."""
        subscriptions = self.sudo().search([('user_id', '=', user.id)])
        if not subscriptions:
            return 0
        if not self._available():
            _logger.warning("pywebpush is not installed: push notifications are disabled")
            return 0
        return sum(1 for subscription in subscriptions if subscription._send_one(payload))
