import json

from odoo import _, fields, models
from odoo.exceptions import UserError

from .geo import PathMeasure


class BusRoute(models.Model):
    _name = 'bus.route'
    _description = 'Bus Route'
    _order = 'code, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    color = fields.Char(default='#3388ff', help="Hex color used on the map.")
    active = fields.Boolean(default=True)
    public = fields.Boolean(default=True, string="Visible to passengers",
                            help="Shown on the public page where passengers see the buses of a route.")
    stop_ids = fields.One2many('bus.route.stop', 'route_id', string="Stops")
    vehicle_ids = fields.One2many('bus.vehicle', 'route_id', string="Buses")
    track_json = fields.Text(string="Recorded track", copy=False, groups='bus_tracking.group_bus_manager')
    track_points = fields.Integer(string="Points of the recorded track", compute='_compute_counts')
    stop_count = fields.Integer(compute='_compute_counts')
    vehicle_count = fields.Integer(compute='_compute_counts')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', "Route code must be unique."),
    ]

    def _recorded_points(self):
        self.ensure_one()
        try:
            points = json.loads(self.sudo().track_json or '[]')
        except ValueError:
            return []
        return points if len(points) > 1 else []

    def _map_lines(self):
        """The line drawn on the maps and used for the deviation alert: the track recorded from a real
        trip when there is one, otherwise the stops joined in order."""
        self.ensure_one()
        points = self._recorded_points() or [[stop.latitude, stop.longitude] for stop in self.stop_ids]
        if len(points) < 2:
            return []
        length = PathMeasure(points).length / 1000.0
        return [{'name': self.name, 'km': round(length, 1), 'points': points}]

    def action_record_track(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Record the track from a bus"),
            'res_model': 'bus.route.record',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_route_id': self.id, 'default_vehicle_id': self.vehicle_ids[:1].id},
        }

    def action_clear_track(self):
        self.write({'track_json': False})

    def _compute_counts(self):
        for route in self:
            route.track_points = len(route._recorded_points())
            route.stop_count = len(route.stop_ids)
            route.vehicle_count = len(route.vehicle_ids)


class BusRouteStop(models.Model):
    _name = 'bus.route.stop'
    _description = 'Bus Route Stop'
    _order = 'route_id, sequence, id'

    route_id = fields.Many2one('bus.route', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    latitude = fields.Float(digits=(10, 7), required=True)
    longitude = fields.Float(digits=(10, 7), required=True)
    radius = fields.Integer(default=50, help="Arrival radius in meters.")


class BusStopArrival(models.Model):
    _name = 'bus.stop.arrival'
    _description = 'Bus Stop Arrival'
    _order = 'arrival_time desc, id desc'

    vehicle_id = fields.Many2one('bus.vehicle', required=True, ondelete='cascade', index=True)
    stop_id = fields.Many2one('bus.route.stop', required=True, ondelete='cascade', index=True)
    route_id = fields.Many2one(related='stop_id.route_id', store=True, index=True)
    arrival_time = fields.Datetime(required=True)
