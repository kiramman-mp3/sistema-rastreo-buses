import base64
import logging
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Both hold the raw badge token, which signs the driver in: only managers may read them.
    driver_badge_qr = fields.Binary(string="Driver badge QR", readonly=True, copy=False,
                                    groups='bus_tracking.group_bus_manager')
    driver_badge_link = fields.Char(string="Badge link", readonly=True, copy=False,
                                    groups='bus_tracking.group_bus_manager')
    driver_badge_active = fields.Boolean(
        string="Badge active",
        compute='_compute_driver_badge_active',
        help="Whether the driver has a valid QR badge.",
    )
    is_bus_driver = fields.Boolean(
        string="Is a driver",
        compute='_compute_is_bus_driver',
        search='_search_is_bus_driver',
        inverse='_inverse_is_bus_driver',
    )
    driver_password = fields.Char(
        string="Password",
        copy=False,
        store=False,
        help="Type here to set or change the driver's password.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Drivers only use the tablet API, so they are portal users: they cannot open the Odoo
        # backend nor read the company's contacts and users. The form sends the default internal
        # groups along, so they are replaced, not added to.
        driver_group = self.env.ref('bus_tracking.group_bus_driver', raise_if_not_found=False)
        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        for vals in vals_list:
            if driver_group and portal_group and vals.get(
                    'is_bus_driver', self.env.context.get('default_is_bus_driver')):
                vals['groups_id'] = [(6, 0, [portal_group.id, driver_group.id])]
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
        # Only the Driver role changes; the user type is left alone (new drivers are created
        # as portal users in `create`).
        driver_group = self.env.ref('bus_tracking.group_bus_driver', raise_if_not_found=False)
        if not driver_group:
            return
        for user in self:
            user.write({'groups_id': [(4 if user.is_bus_driver else 3, driver_group.id)]})

    @api.depends('driver_badge_qr')
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

    def _check_badge_manager(self):
        # The buttons are hidden in the view, but the methods can be called over RPC.
        if not (self.env.su or self.env.user.has_group('bus_tracking.group_bus_manager')):
            raise AccessError(_("Only managers can issue or revoke QR badges."))

    def action_generate_driver_badge(self):
        self.ensure_one()
        self._check_badge_manager()
        if not self.has_group('bus_tracking.group_bus_driver'):
            raise UserError(_("The user must be in the Driver group to have a QR badge."))

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
        self._check_badge_manager()
        for user in self:
            self.env['bus.driver.token']._revoke_badge(user)
            user.sudo().write({
                'driver_badge_qr': False,
                'driver_badge_link': False,
            })
        return True
