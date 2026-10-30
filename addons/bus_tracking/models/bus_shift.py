from odoo import fields, models


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
