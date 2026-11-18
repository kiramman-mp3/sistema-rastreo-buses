import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .geo import PathMeasure

# Measured lines per route, per worker. The deviation alert needs one on every position of every
# bus; decoding up to 1,500 points each time was the cost. The key changes whenever the route,
# its track or any of its stops is edited, so a stale line is never used.
_MEASURES = {}
# Average speed of a city bus, stops and traffic included: it estimates the minutes of a line without a timetable.
# The office can change it with the system parameter bus_tracking.eta_speed_kmh.
ETA_SPEED_KMH = 20.0
_MEASURES_MAX = 64


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
    distance_km = fields.Float(
        compute='_compute_distance_km', store=True, digits=(10, 2),
        help="Length of the line of the route (the recorded track, or the stops joined in order): "
             "the estimated distance.")
    origin_stop_id = fields.Many2one('bus.route.stop', compute='_compute_ends', string="From")
    destination_stop_id = fields.Many2one('bus.route.stop', compute='_compute_ends', string="To")
    schedule_ids = fields.One2many('bus.route.schedule', 'route_id', string="Schedules")

    _sql_constraints = [
        ('code_uniq', 'unique(code)', "Route code must be unique."),
    ]

    @api.constrains('color')
    def _check_color(self):
        for route in self:
            if route.color and not re.match(r'^#[0-9a-fA-F]{6}$', route.color):
                raise ValidationError(_("The color must look like #1e5560."))

    @api.depends('track_json', 'stop_ids.latitude', 'stop_ids.longitude', 'stop_ids.sequence')
    def _compute_distance_km(self):
        for route in self:
            points = route._recorded_points() or [[stop.latitude, stop.longitude] for stop in route.stop_ids]
            route.distance_km = round(PathMeasure(points).length / 1000.0, 2) if len(points) > 1 else 0.0

    @api.depends('stop_ids.sequence')
    def _compute_ends(self):
        for route in self:
            route.origin_stop_id = route.stop_ids[:1]
            route.destination_stop_id = route.stop_ids[-1:] if len(route.stop_ids) > 1 else False

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

    def _path_measure(self):
        """The measured line of `_map_lines`, or None when the route has no line."""
        self.ensure_one()
        stops = self.stop_ids
        key = (self.env.cr.dbname, self.id, self.write_date, len(stops),
               max(stops.mapped('write_date'), default=None))
        if key not in _MEASURES:
            lines = self._map_lines()
            if len(_MEASURES) >= _MEASURES_MAX:
                _MEASURES.clear()
            _MEASURES[key] = PathMeasure(lines[0]['points']) if lines else None
        return _MEASURES[key]

    def _stop_minutes(self):
        """Minutes from the first stop to each stop, for the passengers' estimate: the planned minutes when the
        line has them, otherwise the ones estimated from the distance."""
        self.ensure_one()
        planned = self.stop_ids.mapped('planned_offset_min')
        if any(planned):
            return planned
        return self._distance_minutes() or planned

    def _distance_minutes(self):
        """Minutes from the first stop to each stop along the line at the average speed of a city bus, or an
        empty list when the line has no path to measure."""
        self.ensure_one()
        measure = self._path_measure()
        if not measure:
            return []
        try:
            speed = float(self.env['ir.config_parameter'].sudo().get_param('bus_tracking.eta_speed_kmh') or 0)
        except ValueError:
            speed = 0
        speed = speed if speed > 0 else ETA_SPEED_KMH
        minutes, along = [], 0.0
        for stop in self.stop_ids:
            # a recorded track that loops could place a stop behind the previous one: never go back
            along = max(along, measure.locate(stop.latitude, stop.longitude)[0])
            minutes.append(round(along / 1000.0 / speed * 60.0, 1))
        return minutes

    def _trip_minutes(self):
        """The average minutes the buses took from the first stop to each stop in the finished real trips of the
        line, or None for a stop no trip reached."""
        self.ensure_one()
        arrivals = self.env['bus.trip.stop'].search([
            ('trip_id.route_id', '=', self.id), ('trip_id.simulated', '=', False),
            ('trip_id.state', 'in', ('done', 'incomplete')), ('trip_id.real_start', '!=', False),
            ('actual_time', '!=', False)])
        spent = {}
        for arrival in arrivals:
            minutes = (arrival.actual_time - arrival.trip_id.real_start).total_seconds() / 60.0
            if minutes >= 0:
                spent.setdefault(arrival.stop_id.id, []).append(minutes)
        return [sum(spent[stop.id]) / len(spent[stop.id]) if stop.id in spent else None for stop in self.stop_ids]

    def _set_planned_minutes(self, minutes):
        """Write the planned minutes: 0 at the first stop and never going back along the line."""
        stops = self.stop_ids
        values, last = [], 0
        for index, value in enumerate(minutes):
            last = 0 if index == 0 else max(last, int(round(value)))
            values.append(last)
        # zero first and fill from the end, so the order rule holds after every single write
        stops.write({'planned_offset_min': 0})
        for stop, value in reversed(list(zip(stops, values))):
            stop.planned_offset_min = value

    def action_plan_minutes_distance(self):
        self.ensure_one()
        minutes = self._distance_minutes()
        if len(minutes) < 2:
            raise UserError(_("The line needs at least two stops to measure the distance."))
        self._set_planned_minutes(minutes)
        return True

    def action_plan_minutes_trips(self):
        self.ensure_one()
        real = self._trip_minutes()
        if not any(value is not None for value in real[1:]):
            raise UserError(_("This line has no finished trips with arrivals yet. Use the minutes by distance."))
        # a stop no bus reached yet takes the distance estimate, so the line still gets a full timetable
        distance = self._distance_minutes() or [0.0] * len(real)
        self._set_planned_minutes([r if r is not None else d for r, d in zip(real, distance)])
        return True

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

    def action_load_gpx(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Load the track from a GPX file"),
            'res_model': 'bus.route.gpx',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_route_id': self.id},
        }

    def action_add_stop_on_map(self):
        self.ensure_one()
        return self.env['bus.route.stop']._open_map_picker(self.id)

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
    planned_offset_min = fields.Integer(
        string="Planned minutes", default=0,
        help="Minutes after the bus leaves the first stop that it should be at this one. The first stop is 0.")

    @api.constrains('planned_offset_min', 'sequence', 'route_id')
    def _check_planned_offset(self):
        """The planned minutes never go back along the route."""
        for route in self.mapped('route_id'):
            previous = 0
            for stop in route.stop_ids.sorted(lambda s: (s.sequence, s.id)):
                if stop.planned_offset_min < 0 or stop.planned_offset_min < previous:
                    raise ValidationError(_("The planned minutes of the stops cannot go back along the route "
                                            "(check %s).", stop.name))
                previous = stop.planned_offset_min

    @api.constrains('latitude', 'longitude', 'radius')
    def _check_place(self):
        # The map picker checks this too, but stops can also be typed in the list or imported.
        for stop in self:
            if not (-90 <= stop.latitude <= 90 and -180 <= stop.longitude <= 180):
                raise ValidationError(_("Latitude must be between -90 and 90, and longitude between -180 and 180."))
            if not 5 <= stop.radius <= 1000:
                raise ValidationError(_("The arrival radius must be between 5 and 1000 meters."))

    @api.model
    def _open_map_picker(self, route_id, stop_id=False):
        return {
            'type': 'ir.actions.client',
            'tag': 'bus_tracking.stop_picker',
            'name': _("Stop on the map"),
            'target': 'new',
            'params': {'route_id': route_id, 'stop_id': stop_id},
        }

    def action_pick_on_map(self):
        self.ensure_one()
        return self._open_map_picker(self.route_id.id, self.id)

    @api.model
    def _save_from_map(self, route_id, stop_id, name, latitude, longitude, radius):
        """Create a stop at the end of the route, or move and rename an existing one."""
        if not self.env.user.has_group('bus_tracking.group_bus_manager'):
            raise AccessError(_("Only managers can edit stops."))
        name = (name or '').strip()
        try:
            latitude, longitude, radius = float(latitude), float(longitude), int(radius)
        except (TypeError, ValueError):
            raise UserError(_("Choose a point on the map."))
        if not name:
            raise UserError(_("The stop needs a name."))
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise UserError(_("That point is not on the map."))
        if not 5 <= radius <= 1000:
            raise UserError(_("The arrival radius must be between 5 and 1000 meters."))
        values = {'name': name[:128], 'latitude': round(latitude, 7), 'longitude': round(longitude, 7),
                  'radius': radius}
        if stop_id:
            stop = self.browse(int(stop_id)).exists()
            if not stop or stop.route_id.id != int(route_id):
                raise UserError(_("That stop does not belong to this route."))
            stop.write(values)
            return stop
        route = self.env['bus.route'].browse(int(route_id)).exists()
        if not route:
            raise UserError(_("That route no longer exists."))
        last = route.stop_ids[-1:].sequence or 0
        return self.create(dict(values, route_id=route.id, sequence=last + 10))


class BusStopArrival(models.Model):
    _name = 'bus.stop.arrival'
    _description = 'Bus Stop Arrival'
    _order = 'arrival_time desc, id desc'

    vehicle_id = fields.Many2one('bus.vehicle', required=True, ondelete='cascade', index=True)
    stop_id = fields.Many2one('bus.route.stop', required=True, ondelete='cascade', index=True)
    route_id = fields.Many2one(related='stop_id.route_id', store=True, index=True)
    arrival_time = fields.Datetime(required=True)
