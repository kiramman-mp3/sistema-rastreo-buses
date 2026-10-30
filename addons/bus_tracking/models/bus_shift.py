from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

STALE_AFTER = timedelta(hours=14)


class BusShift(models.Model):
    _name = 'bus.shift'
    _description = 'Driver Shift'
    _order = 'start desc, id desc'

    user_id = fields.Many2one('res.users', string="Driver", required=True, ondelete='cascade', index=True)
    vehicle_id = fields.Many2one('bus.vehicle', required=True, ondelete='cascade', index=True)
    route_id = fields.Many2one('bus.route', required=True, ondelete='restrict', index=True)
    start = fields.Datetime(required=True, default=fields.Datetime.now)
    end = fields.Datetime()
    state = fields.Selection([('active', "Active"), ('done', "Done")], required=True, default='active', index=True)

    def init(self):
        # A driver drives one bus at a time and a bus has one driver at a time, enforced by the database.
        self.env.cr.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS bus_shift_one_active_user_idx "
            "ON bus_shift (user_id) WHERE state = 'active'")
        self.env.cr.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS bus_shift_one_active_vehicle_idx "
            "ON bus_shift (vehicle_id) WHERE state = 'active'")

    def _assign_vehicle(self):
        """The live map reads bus.vehicle.driver_id (a partner), not the Odoo user."""
        for shift in self:
            shift.vehicle_id.sudo().write({
                'driver_id': shift.user_id.partner_id.id,
                'route_id': shift.route_id.id,
            })

    def _end(self):
        now = fields.Datetime.now()
        for shift in self:
            bus = shift.vehicle_id.sudo()
            shift.write({'state': 'done', 'end': now})
            if bus.driver_id == shift.user_id.partner_id:
                bus.driver_id = False

    def action_revoke_tablet(self):
        """Drop every app token of this driver so the tablet must log in again."""
        if not self.env.user.has_group('bus_tracking.group_bus_manager'):
            raise AccessError(_("Only managers can sign a tablet out."))
        Token = self.env['bus.driver.token']
        for shift in self:
            Token._revoke_user(shift.user_id)
            if shift.state == 'active':
                shift.sudo()._end()

    @api.model
    def _cron_close_stale(self):
        stale = self.search([
            ('state', '=', 'active'),
            ('start', '<', fields.Datetime.now() - STALE_AFTER),
        ])
        stale._end()
