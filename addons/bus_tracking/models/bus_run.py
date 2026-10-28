from datetime import timedelta

from odoo import api, fields, models

STALE_AFTER = timedelta(hours=12)


class BusRun(models.Model):
    """One trip between the two ends of a route, written by the system from the bus positions:
    it starts when the bus leaves an end and finishes when it reaches the other one."""
    _name = 'bus.run'
    _description = 'Bus Run'
    _order = 'departure desc, id desc'

    vehicle_id = fields.Many2one('bus.vehicle', string="Bus", required=True, ondelete='cascade', index=True)
    route_id = fields.Many2one('bus.route', string="Route", required=True, ondelete='cascade', index=True)
    origin_stop_id = fields.Many2one('bus.route.stop', string="From", required=True, ondelete='cascade')
    destination_stop_id = fields.Many2one('bus.route.stop', string="To", ondelete='cascade')
    departure = fields.Datetime(required=True, index=True)
    arrival = fields.Datetime()
    state = fields.Selection([('running', "On the way"), ('done', "Arrived")], required=True,
                             default='running', index=True)
    duration_minutes = fields.Float(compute='_compute_duration', string="Duration")

    @api.depends('departure', 'arrival')
    def _compute_duration(self):
        for run in self:
            run.duration_minutes = (run.arrival - run.departure).total_seconds() / 60.0 if run.arrival else 0.0

    @api.model
    def _on_stop_change(self, vehicle, previous, current, when):
        """Called when the stop a bus is standing in changes (either may be empty)."""
        stops = vehicle.route_id.stop_ids
        if len(stops) < 2:
            return
        ends = stops[0] | stops[-1]
        running = self.search([('vehicle_id', '=', vehicle.id), ('state', '=', 'running')])
        # A trip of another route, or one that never ended, is not a trip of this bus any more.
        stale = running.filtered(lambda run: run.route_id != vehicle.route_id)
        stale.unlink()
        running -= stale
        if current in ends and running:
            run = running[0]
            if current == run.origin_stop_id:
                run.unlink()                        # came back without reaching the other end
            else:
                run.write({'state': 'done', 'arrival': when, 'destination_stop_id': current.id})
            running = self.browse()
        if previous in ends and current != previous and current not in ends and not running:
            self.create({
                'vehicle_id': vehicle.id,
                'route_id': vehicle.route_id.id,
                'origin_stop_id': previous.id,
                'departure': when,
            })

    @api.model
    def _cron_discard_stale(self):
        """A trip still open after many hours was left (a phone switched off): it is not a real trip."""
        self.search([('state', '=', 'running'), ('departure', '<', fields.Datetime.now() - STALE_AFTER)]).unlink()
