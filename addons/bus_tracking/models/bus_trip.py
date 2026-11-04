"""Scheduled trips: the planned side of a trip (route, bus, date, times) and, in the same record, what really happened.

A schedule says "line L1 leaves at 07:15 on weekdays"; the planned minutes of each stop come from the route
(`bus.route.stop.planned_offset_min`). A trip is that schedule on one date for one bus, and keeps a line per stop
with the planned and the real time.
"""
import logging
from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .utils import int_param

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
