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

    def _trip_progress(self):
        """Where the bus is on its current trip: the stops in the order it travels them, the time it
        reached each one on this trip, and the next stop. A trip starts at the shift start or at the
        last time the bus reached an end of the route; after reaching the last stop the bus heads
        back, so the stops are walked in reverse."""
        self.ensure_one()
        stops = self.route_id.sudo().stop_ids
        Arrival = self.env['bus.stop.arrival'].sudo()
        trip_start, direction = self.start, 'forward'
        if stops:
            ends = stops[0] | stops[-1]
            last_end = Arrival.search([
                ('vehicle_id', '=', self.vehicle_id.id),
                ('stop_id', 'in', ends.ids),
                ('arrival_time', '>=', self.start),
            ], order='arrival_time desc, id desc', limit=1)
            if last_end:
                trip_start = last_end.arrival_time
                if len(stops) > 1 and last_end.stop_id == stops[-1]:
                    direction = 'back'
        ordered = stops if direction == 'forward' else stops[::-1]
        arrived = {}
        for arrival in Arrival.search([
                ('vehicle_id', '=', self.vehicle_id.id),
                ('stop_id', 'in', stops.ids),
                ('arrival_time', '>=', trip_start),
        ], order='arrival_time desc'):
            arrived.setdefault(arrival.stop_id.id, arrival.arrival_time)
        next_stop = next((stop for stop in ordered if stop.id not in arrived), stops.browse())
        return {'stops': ordered, 'arrived': arrived, 'next_stop': next_stop, 'direction': direction}

    def action_revoke_tablet(self):
        """Drop the driver's tablet sessions so the tablet must log in again; the QR badge is kept."""
        if not self.env.user.has_group('bus_tracking.group_bus_manager'):
            raise AccessError(_("Only managers can sign a tablet out."))
        Token = self.env['bus.driver.token']
        for shift in self:
            Token._revoke_sessions(shift.user_id)
            if shift.state == 'active':
                shift.sudo()._end()

    @api.model
    def _cron_close_stale(self):
        stale = self.search([
            ('state', '=', 'active'),
            ('start', '<', fields.Datetime.now() - STALE_AFTER),
        ])
        stale._end()
