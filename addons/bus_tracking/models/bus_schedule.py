from odoo import fields, models

from .utils import float_to_clock


class BusSchedule(models.Model):
    _name = 'bus.schedule'
    _description = 'Bus Schedule'
    _order = 'vehicle_id, departure, id'

    vehicle_id = fields.Many2one('bus.vehicle', string="Bus", required=True, ondelete='cascade', index=True)
    route_id = fields.Many2one('bus.route', string="Route", required=True, ondelete='cascade', index=True)
    departure = fields.Float(required=True, help="Local time, e.g. 06:30.")
    arrival = fields.Float(required=True, help="Local time, e.g. 07:15.")
    name = fields.Char(compute='_compute_name')

    def _compute_name(self):
        for rec in self:
            rec.name = "%s %s-%s" % (rec.vehicle_id.name or '', float_to_clock(rec.departure), float_to_clock(rec.arrival))
