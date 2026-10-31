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
    is_bus_driver = fields.Boolean(
        string="Es Chofer",
        compute='_compute_is_bus_driver',
        search='_search_is_bus_driver',
        inverse='_inverse_is_bus_driver',
    )
    driver_password = fields.Char(
        string="Contraseña",
        copy=False,
        store=False,
        help="Escribe aquí para asignar o cambiar la contraseña del conductor.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        driver_group = self.env.ref('bus_tracking.group_bus_driver', raise_if_not_found=False)
        internal_group = self.env.ref('base.group_user', raise_if_not_found=False)
        for vals in vals_list:
            if vals.get('is_bus_driver', self.env.context.get('default_is_bus_driver')):
                groups = list(vals.get('groups_id', []))
                if driver_group:
                    groups.append((4, driver_group.id))
                if internal_group:
                    groups.append((4, internal_group.id))
                vals['groups_id'] = groups
            if vals.get('driver_password'):
                vals['password'] = vals.pop('driver_password')
        return super(ResUsers, self.with_context(no_reset_password=True)).create(vals_list)

    def write(self, vals):
        if vals.get('driver_password'):
            vals['password'] = vals.pop('driver_password')
        return super(ResUsers, self.with_context(no_reset_password=True)).write(vals)

    def _compute_is_bus_driver(self):
        driver_group = self.env.ref('bus_tracking.group_bus_driver', raise_if_not_found=False)
        for user in self:
            user.is_bus_driver = bool(driver_group and driver_group in user.groups_id)

    def _search_is_bus_driver(self, operator, value):
        driver_group = self.env.ref('bus_tracking.group_bus_driver', raise_if_not_found=False)
        if not driver_group:
            return []
        positive = (operator in ('=', '!=') and value) or (operator == 'in' and True in value)
        if operator in ('!=', '<>'):
            positive = not positive
        if positive:
            return [('groups_id', 'in', [driver_group.id])]
        return [('groups_id', 'not in', [driver_group.id])]

    def _inverse_is_bus_driver(self):
        driver_group = self.env.ref('bus_tracking.group_bus_driver', raise_if_not_found=False)
        internal_group = self.env.ref('base.group_user', raise_if_not_found=False)
        if not driver_group:
            return
        for user in self:
            if user.is_bus_driver:
                groups = [(4, driver_group.id)]
                if internal_group and internal_group not in user.groups_id:
                    groups.append((4, internal_group.id))
                user.write({'groups_id': groups})
            else:
                user.write({'groups_id': [(3, driver_group.id)]})

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
