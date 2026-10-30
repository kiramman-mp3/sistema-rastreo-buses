import hashlib
import secrets
from datetime import timedelta

from odoo import api, fields, models

TOKEN_TTL = timedelta(days=30)


def hash_token(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


class BusDriverToken(models.Model):
    """Bearer token the tablet app keeps after a driver logs in. Only the hash is
    stored, so a database leak does not hand out working sessions."""
    _name = 'bus.driver.token'
    _description = 'Driver App Token'
    _order = 'id desc'

    token_hash = fields.Char(required=True, index=True, readonly=True)
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    device_label = fields.Char()
    expires = fields.Datetime(required=True)

    _sql_constraints = [
        ('token_hash_uniq', 'unique(token_hash)', "Token already exists."),
    ]

    @api.model
    def _issue(self, user, device_label=''):
        """Create a token for `user` and return the raw value, which is never stored."""
        raw = secrets.token_urlsafe(32)
        self.sudo().create({
            'token_hash': hash_token(raw),
            'user_id': user.id,
            'device_label': (device_label or '')[:80],
            'expires': fields.Datetime.now() + TOKEN_TTL,
        })
        return raw

    @api.model
    def _user_for(self, raw):
        """The driver the token belongs to, or an empty recordset when it is unknown,
        expired, or its user lost the driver role."""
        users = self.env['res.users']
        if not raw:
            return users
        token = self.sudo().search([
            ('token_hash', '=', hash_token(raw)), ('expires', '>', fields.Datetime.now())], limit=1)
        user = token.user_id
        if user.active and user.has_group('bus_tracking.group_bus_driver'):
            return user
        return users

    @api.model
    def _revoke(self, raw):
        self.sudo().search([('token_hash', '=', hash_token(raw))]).unlink()

    @api.model
    def _cron_purge(self):
        self.sudo().search([('expires', '<', fields.Datetime.now())]).unlink()
