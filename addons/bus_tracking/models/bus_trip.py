"""Scheduled trips: the planned side of a trip (route, bus, date, times) and, in the same record, what really happened.

A schedule says "line L1 leaves at 07:15 on weekdays"; the planned minutes of each stop come from the route
(`bus.route.stop.planned_offset_min`). A trip is that schedule on one date for one bus, and keeps a line per stop
with the planned and the real time.
"""
import logging
from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .geo import thin
from .utils import haversine_m, int_param

_logger = logging.getLogger(__name__)

# Ecuador is UTC-5 all year (utils.LOCAL_TIMEZONE): times are written in local time and stored in UTC.
LOCAL_OFFSET = timedelta(hours=5)
WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')


def local_to_utc(day, hours):
    """The UTC datetime of `hours` (7.25 is 07:15) on the local day `day`."""
    whole = int(hours)
    minutes = int(round((hours - whole) * 60))
    return datetime.combine(day, time(0, 0)) + timedelta(hours=whole, minutes=minutes) + LOCAL_OFFSET


def utc_to_local_date(moment):
    return (moment - LOCAL_OFFSET).date()


def hours_text(hours):
    hh, mm = divmod(int(round(hours * 60)), 60)
    return '%02d:%02d' % (hh % 24, mm)


class BusRouteSchedule(models.Model):
    _name = 'bus.route.schedule'
    _description = 'Route Schedule'
    _order = 'route_id, departure_time, id'

    name = fields.Char(compute='_compute_name', store=True)
    route_id = fields.Many2one('bus.route', required=True, ondelete='cascade', index=True)
    departure_time = fields.Float(
        required=True, default=7.0, help="Local time the bus leaves the first stop (hours and minutes).")
    monday = fields.Boolean(default=True)
    tuesday = fields.Boolean(default=True)
    wednesday = fields.Boolean(default=True)
    thursday = fields.Boolean(default=True)
    friday = fields.Boolean(default=True)
    saturday = fields.Boolean(default=False)
    sunday = fields.Boolean(default=False)
    vehicle_id = fields.Many2one(
        'bus.vehicle', string="Default bus", ondelete='set null',
        help="The bus that does this schedule. Trips are created for it every day for the next few days.")
    active = fields.Boolean(default=True)
    arrival_time = fields.Float(compute='_compute_arrival_time', help="Planned local time of arrival at the last stop.")

    @api.depends('route_id.code', 'departure_time')
    def _compute_name(self):
        for schedule in self:
            schedule.name = '%s %s' % (schedule.route_id.code or '', hours_text(schedule.departure_time))

    @api.depends('departure_time', 'route_id.stop_ids.planned_offset_min')
    def _compute_arrival_time(self):
        for schedule in self:
            offsets = schedule.route_id.stop_ids.mapped('planned_offset_min')
            schedule.arrival_time = schedule.departure_time + max(offsets or [0]) / 60.0

    @api.constrains('departure_time', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    def _check_schedule(self):
        for schedule in self:
            if not 0 <= schedule.departure_time < 24:
                raise ValidationError(_("The departure time must be between 00:00 and 23:59."))
            if not any(getattr(schedule, day) for day in WEEKDAYS):
                raise ValidationError(_("Choose at least one day of the week."))

    def action_assign_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Assign a bus"),
            'res_model': 'bus.trip.assign',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_schedule_id': self.id, 'default_vehicle_id': self.vehicle_id.id},
        }

    def _runs_on(self, day):
        self.ensure_one()
        return bool(getattr(self, WEEKDAYS[day.weekday()]))

    def _generate_trips(self, date_from, date_to, vehicle=None, strict=False):
        """Create the trips of these schedules for each local day between the two dates (both included).
        Existing ones are kept. With `strict` a clash with another trip of the bus raises; without it the
        day is skipped, so one bad day never stops the rest (the cron)."""
        Trip = self.env['bus.trip']
        created = Trip
        for schedule in self:
            bus = vehicle or schedule.vehicle_id
            if not bus:
                continue
            day = date_from
            while day <= date_to:
                start = local_to_utc(day, schedule.departure_time)
                if schedule._runs_on(day) and not Trip.search_count([
                        ('vehicle_id', '=', bus.id), ('schedule_id', '=', schedule.id), ('planned_start', '=', start)]):
                    values = {'vehicle_id': bus.id, 'route_id': schedule.route_id.id,
                              'schedule_id': schedule.id, 'planned_start': start}
                    if strict:
                        created |= Trip.create(values)
                    else:
                        try:
                            with self.env.cr.savepoint():
                                created |= Trip.create(values)
                        except ValidationError as error:
                            _logger.warning("Trip of %s on %s not created: %s", schedule.name, day, error.args[0])
                day += timedelta(days=1)
        return created

    @api.model
    def _cron_generate_trips(self):
        today = utc_to_local_date(fields.Datetime.now())
        horizon = max(int_param(self.env, 'bus_tracking.trip_horizon_days', 2), 0)
        self.search([('vehicle_id', '!=', False)])._generate_trips(today, today + timedelta(days=horizon))


class BusTrip(models.Model):
    _name = 'bus.trip'
    _description = 'Scheduled Trip'
    _order = 'planned_start desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    vehicle_id = fields.Many2one('bus.vehicle', string="Bus", required=True, ondelete='cascade', index=True)
    route_id = fields.Many2one('bus.route', string="Route", required=True, ondelete='cascade', index=True)
    schedule_id = fields.Many2one('bus.route.schedule', string="Schedule", ondelete='set null')
    date = fields.Date(compute='_compute_date', store=True, index=True, help="Local date of the planned departure.")
    planned_start = fields.Datetime(required=True, index=True)
    planned_end = fields.Datetime(compute='_compute_planned_end', store=True)
    state = fields.Selection(
        [('planned', "Planned"), ('running', "On the way"), ('done', "Done"),
         ('incomplete', "Incomplete"), ('cancelled', "Cancelled")],
        required=True, default='planned', index=True)
    simulated = fields.Boolean(
        default=False, index=True,
        help="Created by the trip simulator, not driven by a bus. Never mixed with real data silently.")
    scenario = fields.Char(help="What the simulator was told to do on this trip.")
    stop_line_ids = fields.One2many('bus.trip.stop', 'trip_id', string="Stops")
    stop_count = fields.Integer(compute='_compute_stop_count')

    # What really happened
    real_start = fields.Datetime(readonly=True, help="When the bus reached its first stop of this trip.")
    real_end = fields.Datetime(readonly=True, help="When the bus reached its last stop of this trip.")
    distance_est_km = fields.Float(
        digits=(10, 2), help="Estimated distance: the length of the route when the trip was planned.")
    distance_real_km = fields.Float(
        digits=(10, 2), readonly=True, help="Distance driven between the first and the last position of the trip.")
    duration_est_min = fields.Float(compute='_compute_durations', store=True, string="Planned duration (min)")
    duration_real_min = fields.Float(compute='_compute_durations', store=True, string="Real duration (min)")
    duration_diff_pct = fields.Float(compute='_compute_durations', store=True, string="Duration difference (%)")
    time_flag = fields.Boolean(
        readonly=True, help="The real duration differs from the planned one by more than the tolerance.")
    deviation_avg_m = fields.Float(
        readonly=True, help="Average distance of the positions of the trip to the line of the route.")
    deviation_max_m = fields.Float(readonly=True)
    corridor_pct = fields.Float(readonly=True, help="Share of the positions inside the corridor around the route.")
    stops_total = fields.Integer(compute='_compute_stats', store=True)
    stops_visited = fields.Integer(compute='_compute_stats', store=True)
    stops_late = fields.Integer(compute='_compute_stats', store=True)
    stops_skipped = fields.Integer(compute='_compute_stats', store=True)
    delay_avg_min = fields.Float(compute='_compute_stats', store=True, help="Average delay of the late arrivals.")
    delay_max_min = fields.Float(
        compute='_compute_stats', store=True, help="Largest delay of the trip (0 when nothing was late).")
    delay_end_min = fields.Float(
        compute='_compute_stats', store=True, help="Delay at the last stop reached: the delay the trip piled up.")
    alert_ids = fields.One2many('bus.alert', 'trip_id', string="Alerts")
    incident_ids = fields.One2many('bus.incident', 'trip_id', string="Incidents")
    alert_count = fields.Integer(compute='_compute_counts')
    incident_count = fields.Integer(compute='_compute_counts')

    @api.depends('route_id.code', 'vehicle_id.name', 'planned_start')
    def _compute_name(self):
        for trip in self:
            local = trip.planned_start and (trip.planned_start - LOCAL_OFFSET)
            trip.name = '%s · %s · %s' % (
                trip.route_id.code or '', trip.vehicle_id.name or '',
                local.strftime('%Y-%m-%d %H:%M') if local else '')

    @api.depends('planned_start')
    def _compute_date(self):
        for trip in self:
            trip.date = utc_to_local_date(trip.planned_start) if trip.planned_start else False

    @api.depends('planned_start', 'route_id.stop_ids.planned_offset_min')
    def _compute_planned_end(self):
        for trip in self:
            offsets = trip.route_id.stop_ids.mapped('planned_offset_min')
            trip.planned_end = (trip.planned_start + timedelta(minutes=max(offsets or [0]))
                                if trip.planned_start else False)

    def _compute_stop_count(self):
        for trip in self:
            trip.stop_count = len(trip.stop_line_ids)

    def _compute_counts(self):
        for trip in self:
            trip.alert_count = len(trip.alert_ids)
            trip.incident_count = len(trip.incident_ids)

    @api.depends('planned_start', 'planned_end', 'real_start', 'real_end')
    def _compute_durations(self):
        for trip in self:
            planned = (trip.planned_end - trip.planned_start).total_seconds() / 60.0 if trip.planned_end else 0.0
            real = 0.0
            if trip.real_start and trip.real_end:
                real = (trip.real_end - trip.real_start).total_seconds() / 60.0
            trip.duration_est_min = planned
            trip.duration_real_min = real
            trip.duration_diff_pct = (real - planned) / planned * 100.0 if planned and real else 0.0

    @api.depends('stop_line_ids.status', 'stop_line_ids.delay_min', 'stop_line_ids.actual_time')
    def _compute_stats(self):
        for trip in self:
            lines = trip.stop_line_ids.sorted(lambda ln: (ln.sequence, ln.id))
            arrived = lines.filtered('actual_time')
            late = lines.filtered(lambda ln: ln.status == 'late')
            trip.stops_total = len(lines)
            trip.stops_visited = len(arrived)
            trip.stops_late = len(late)
            trip.stops_skipped = len(lines.filtered(lambda ln: ln.status == 'skipped'))
            trip.delay_avg_min = sum(late.mapped('delay_min')) / len(late) if late else 0.0
            trip.delay_max_min = max(arrived.mapped('delay_min') + [0.0])
            trip.delay_end_min = arrived[-1].delay_min if arrived else 0.0

    @api.constrains('planned_start', 'planned_end')
    def _check_planned_times(self):
        for trip in self:
            if trip.planned_start and trip.planned_end and trip.planned_end <= trip.planned_start:
                raise ValidationError(_("The stops of this route have no planned times: set the minutes "
                                        "of each stop before scheduling trips."))

    @api.constrains('vehicle_id', 'planned_start', 'planned_end', 'state')
    def _check_overlap(self):
        """One bus cannot do two trips at once; the same bus can do other routes at other times."""
        for trip in self.filtered(lambda t: t.state != 'cancelled' and t.planned_end):
            clash = self.search([
                ('id', '!=', trip.id), ('vehicle_id', '=', trip.vehicle_id.id), ('state', '!=', 'cancelled'),
                ('planned_start', '<', trip.planned_end), ('planned_end', '>', trip.planned_start)], limit=1)
            if clash:
                raise ValidationError(_("%(bus)s already has the trip %(trip)s at that time.",
                                        bus=trip.vehicle_id.name, trip=clash.name))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'distance_est_km' not in values and values.get('route_id'):
                values['distance_est_km'] = self.env['bus.route'].browse(values['route_id']).distance_km
        trips = super().create(vals_list)
        lines = []
        for trip in trips:
            for stop in trip.route_id.stop_ids:
                lines.append({
                    'trip_id': trip.id, 'stop_id': stop.id, 'sequence': stop.sequence,
                    'planned_time': trip.planned_start + timedelta(minutes=stop.planned_offset_min),
                })
        self.env['bus.trip.stop'].create(lines)
        return trips

    def action_cancel(self):
        self.filtered(lambda t: t.state in ('planned', 'running')).write({'state': 'cancelled'})

    # ------------------------------------------------------------------
    # What happens on the road
    # ------------------------------------------------------------------
    @api.model
    def _trips_around(self, vehicle, when, states=('planned', 'running'), route=None):
        """The trips of the bus whose planned window, widened by the margin, holds `when`; the closest start first."""
        margin = timedelta(minutes=int_param(self.env, 'bus_tracking.trip_margin_min', 30))
        domain = [('vehicle_id', '=', vehicle.id), ('state', 'in', states),
                  ('planned_start', '<=', when + margin), ('planned_end', '>=', when - margin)]
        if route:
            domain.append(('route_id', '=', route.id))
        return self.search(domain).sorted(lambda t: abs((t.planned_start - when).total_seconds()))

    @api.model
    def _trip_at(self, vehicle, when):
        """The trip a bus was on at `when` (also a finished one): where an alert or an incident belongs."""
        return self._trips_around(vehicle, when, ('planned', 'running', 'done', 'incomplete'))[:1]

    @api.model
    def _on_arrival(self, arrival):
        """A bus entered the radius of a stop: it belongs to the planned trip of that route whose window
        holds the time."""
        trip = self._trips_around(arrival.vehicle_id, arrival.arrival_time, route=arrival.stop_id.route_id)[:1]
        if trip:
            trip._register_arrival(arrival)

    def _register_arrival(self, arrival):
        self.ensure_one()
        lines = self.stop_line_ids.sorted(lambda ln: (ln.sequence, ln.id))
        line = lines.filtered(lambda ln: ln.stop_id == arrival.stop_id)[:1]
        if not line or line.actual_time:
            return
        tolerance = int_param(self.env, 'bus_tracking.punctuality_tolerance_min', 5)
        delay = (arrival.arrival_time - line.planned_time).total_seconds() / 60.0
        line.write({
            'actual_time': arrival.arrival_time,
            'delay_min': delay,
            'status': 'late' if delay > tolerance else ('early' if delay < -tolerance else 'on_time'),
        })
        if self.state == 'planned':
            self.write({'state': 'running', 'real_start': arrival.arrival_time})
        if line == lines[-1]:
            self._finalize(arrival.arrival_time)

    def _finalize(self, end_time=None):
        """Close the trips: the stops never reached are skipped; reaching every stop is a done trip, anything else
        an incomplete one. Then measure what was driven."""
        for trip in self.filtered(lambda t: t.state in ('planned', 'running')):
            lines = trip.stop_line_ids
            lines.filtered(lambda ln: ln.status == 'pending').write({'status': 'skipped'})
            visited = lines.filtered('actual_time')
            skipped = lines.filtered(lambda ln: ln.status == 'skipped')
            trip.write({
                'state': 'done' if visited and not skipped else 'incomplete',
                'real_end': max(visited.mapped('actual_time')) if visited else False,
            })
            trip._compute_real_figures()

    def _compute_real_figures(self):
        """Distance driven and how far from the line of the route, from the positions stored during the trip."""
        Position = self.env['bus.position']
        corridor = int_param(self.env, 'bus_tracking.off_route_meters', 150) or 150
        for trip in self:
            start = trip.real_start or trip.planned_start
            end = trip.real_end or trip.planned_end
            positions = Position.search([
                ('vehicle_id', '=', trip.vehicle_id.id), ('fix_time', '>=', start), ('fix_time', '<=', end)],
                order='fix_time asc')
            points = thin([(p.latitude, p.longitude) for p in positions], 10)
            values = {'distance_real_km': round(sum(
                haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(points, points[1:])) / 1000.0, 3)}
            measure = trip.route_id._path_measure()
            if measure and points:
                offsets = [measure.locate(lat, lon)[1] for lat, lon in points]
                values.update({
                    'deviation_avg_m': sum(offsets) / len(offsets),
                    'deviation_max_m': max(offsets),
                    'corridor_pct': 100.0 * sum(1 for o in offsets if o <= corridor) / len(offsets),
                })
            trip.write(values)

    @api.model
    def _cron_close_trips(self):
        """A trip whose window (and margin) is over is closed with what it has."""
        margin = timedelta(minutes=int_param(self.env, 'bus_tracking.trip_margin_min', 30))
        self.search([('state', 'in', ('planned', 'running')),
                     ('planned_end', '<', fields.Datetime.now() - margin)])._finalize()


class BusTripStop(models.Model):
    _name = 'bus.trip.stop'
    _description = 'Stop of a Scheduled Trip'
    _order = 'trip_id, sequence, id'

    trip_id = fields.Many2one('bus.trip', required=True, ondelete='cascade', index=True)
    stop_id = fields.Many2one('bus.route.stop', required=True, ondelete='cascade')
    sequence = fields.Integer()
    planned_time = fields.Datetime(required=True)
    actual_time = fields.Datetime()
    delay_min = fields.Float(help="Minutes after the planned time (negative: early).")
    status = fields.Selection(
        [('pending', "Pending"), ('on_time', "On time"), ('late', "Late"), ('early', "Early"), ('skipped', "Skipped")],
        required=True, default='pending', index=True)
    route_id = fields.Many2one(related='trip_id.route_id', store=True, index=True)
    vehicle_id = fields.Many2one(related='trip_id.vehicle_id', store=True, index=True)
    date = fields.Date(related='trip_id.date', store=True, index=True)


class BusTripAssign(models.TransientModel):
    _name = 'bus.trip.assign'
    _description = 'Assign a bus to a schedule'

    schedule_id = fields.Many2one('bus.route.schedule', string="Schedule", required=True, ondelete='cascade')
    vehicle_id = fields.Many2one('bus.vehicle', string="Bus", required=True, ondelete='cascade')
    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=lambda self: fields.Date.context_today(self) + timedelta(days=6))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_to < wizard.date_from:
                raise ValidationError(_("The last day cannot be before the first day."))
            if (wizard.date_to - wizard.date_from).days > 92:
                raise ValidationError(_("Assign at most three months at a time."))

    def action_assign(self):
        self.ensure_one()
        trips = self.schedule_id._generate_trips(self.date_from, self.date_to, vehicle=self.vehicle_id, strict=True)
        return {
            'type': 'ir.actions.act_window',
            'name': _("Scheduled trips"),
            'res_model': 'bus.trip',
            'view_mode': 'tree,calendar,form',
            'domain': [('id', 'in', trips.ids)],
        }
