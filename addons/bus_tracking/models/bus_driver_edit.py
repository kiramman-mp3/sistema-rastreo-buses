from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class BusDriverEdit(models.TransientModel):
    """Create or edit a driver. Bus managers need not be Odoo administrators, so they cannot write res.users;
    giving them that right would also let them put a driver in any group (DEF-060). This wizard writes only
    these fields, with sudo, and only on drivers."""
    _name = 'bus.driver.edit'
    _description = 'Create or edit a driver'

    user_id = fields.Many2one('res.users', string="Driver", readonly=True)
    name = fields.Char(required=True)
    login = fields.Char(string="User", required=True)
    password = fields.Char(help="Leave it empty to keep the current password.")
    phone = fields.Char()
    email = fields.Char()
    active = fields.Boolean(default=True, help="An archived driver cannot sign in on the tablet.")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        user = self.env['res.users'].sudo().with_context(active_test=False).browse(values.get('user_id'))
        if user:
            self._check_driver(user)
            values.update(name=user.name, login=user.login, phone=user.phone, email=user.email, active=user.active)
        return values

    @api.model
    def _check_driver(self, user):
        """Only drivers are edited here: never the staff, whose password would open the backend."""
        if not user.has_group('bus_tracking.group_bus_driver') or user.has_group('base.group_user'):
            raise AccessError(_("Only drivers can be edited here."))

    def action_save(self):
        self.ensure_one()
        if not (self.env.su or self.env.user.has_group('bus_tracking.group_bus_manager')):
            raise AccessError(_("Only managers can create or edit drivers."))
        vals = {'name': self.name.strip(), 'login': self.login.strip(), 'phone': self.phone or False,
                'email': self.email or False, 'active': self.active}
        if self.password:
            vals['driver_password'] = self.password
        Users = self.env['res.users'].sudo().with_context(active_test=False)
        if self.user_id:
            user = Users.browse(self.user_id.id)
            self._check_driver(user)
            user.write(vals)
        else:
            user = Users.create(dict(vals, is_bus_driver=True))
        # The wizard row stays in the database until the vacuum: do not leave the password in it.
        self.password = False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'res_id': user.id,
            'view_mode': 'form',
            'views': [(self.env.ref('bus_tracking.view_bus_driver_form').id, 'form')],
            'target': 'current',
        }


class BusDriverBadge(models.TransientModel):
    """A QR badge, shown once right after it is issued. The raw token lives only in this row, which the manager
    deletes by closing it with Done (otherwise the transient vacuum does)."""
    _name = 'bus.driver.badge'
    _description = 'QR badge shown once'
    _transient_max_hours = 0.25

    user_id = fields.Many2one('res.users', string="Driver", readonly=True)
    qr = fields.Binary(string="QR badge", readonly=True, attachment=False)
    link = fields.Char(readonly=True)

    def action_done(self):
        # It deletes as the system, so it checks who asks: any session could otherwise call it over RPC.
        if not (self.env.su or self.env.user.has_group('bus_tracking.group_bus_manager')):
            raise AccessError(_("Only managers can close a QR badge."))
        self.sudo().unlink()
        return {'type': 'ir.actions.act_window_close'}
