import base64
import logging
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    driver_badge_qr = fields.Binary(string="Credencial QR", readonly=True, copy=False)
    driver_badge_link = fields.Char(string="Enlace de Credencial", readonly=True, copy=False)
    driver_badge_active = fields.Boolean(
        string="Credencial activa",
        compute='_compute_driver_badge_active',
        help="Indica si el conductor tiene una credencial QR vigente.",
    )

    def _compute_driver_badge_active(self):
        now = fields.Datetime.now()
        active_tokens = self.env['bus.driver.token'].sudo().search([
            ('user_id', 'in', self.ids),
            ('device_label', '=', 'badge_qr'),
            ('expires', '>', now),
        ])
        users_with_token = set(active_tokens.mapped('user_id.id'))
        for user in self:
            user.driver_badge_active = user.id in users_with_token and bool(user.driver_badge_qr)

    def action_generate_driver_badge(self):
        self.ensure_one()
        if not self.has_group('bus_tracking.group_bus_driver'):
            raise UserError(_("El usuario debe pertenecer al grupo de Choferes para tener una credencial QR."))

        raw = self.env['bus.driver.token']._issue_badge(self)
        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        if base.endswith('/web'):
            base = base[:-4].rstrip('/')

        query = urlencode({'odoo': base, 'token': raw, 'driver': self.name})
        link = f"uta-buses://login?{query}"

        png = self.env['ir.actions.report'].barcode('QR', link, width=280, height=280)
        self.sudo().write({
            'driver_badge_qr': base64.b64encode(png),
            'driver_badge_link': link,
        })
        return True

    def action_revoke_driver_badge(self):
        for user in self:
            self.env['bus.driver.token']._revoke_badge(user)
            user.sudo().write({
                'driver_badge_qr': False,
                'driver_badge_link': False,
            })
        return True
