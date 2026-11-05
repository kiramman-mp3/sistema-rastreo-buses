"""Trip simulator: replays a bus along a route through the same ingestion the real GPS uses.

Nothing about the result is written by hand: the simulator only produces positions, and the rules of
`bus.trip` and `bus.alert` decide what was late, skipped or off the route. Each scenario says what it
expects to be detected, so the detection can be measured (metric S4).

Simulated trips belong to simulated buses (`bus.vehicle.simulated`), which the live map and the public pages
never show, and every trip is marked `simulated` with its scenario: they are never mixed with real data silently.
"""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .bus_trip import local_to_utc, utc_to_local_date
from .utils import haversine_m

PLAN_SPEED_KMH = 22.0          # the speed the planned minutes assume
DWELL_S = 30                   # the bus stays this long at a stop
POSITION_EVERY_S = 60
SIDE_STEP_DEG = 0.0045         # about 500 m: far from the line of the route
START_LOCAL = 7.0              # simulated trips leave at 07:00 local time


def _late(offsets):
    """On time at the first stop, then at least 6 minutes behind the plan (tolerance 5), growing with the route."""
    return [0.0] + [round(max(6.0 + 0.2 * o, 0.4 * o), 1) for o in offsets[1:]]


SCENARIOS = {
    'punctual': {
        'label': "On time", 'flags': (), 'delays': lambda offs: [0.0] * len(offs)},
    'within_tolerance': {
        'label': "A little late, inside the tolerance", 'flags': (),
        'delays': lambda offs: [min(round(o * 0.1, 1), 4.0) for o in offs]},
    'early': {
        'label': "Early", 'flags': ('early',), 'delays': lambda offs: [-7.0] * len(offs)},
    'late': {
        'label': "Late", 'flags': ('late',), 'delays': _late},
    'skipped_stop': {
        'label': "A middle stop skipped", 'flags': ('skipped', 'incomplete'),
        'delays': lambda offs: [0.0] * len(offs), 'skip': 'middle'},
    'incomplete_end': {
        'label': "Stopped before the last stop", 'flags': ('skipped', 'incomplete'),
        'delays': lambda offs: [0.0] * len(offs), 'stop_before_end': True},
    'deviation': {
        'label': "Off the route on the longest stretch", 'flags': ('off_route',),
        'delays': lambda offs: [0.0] * len(offs), 'off_route': True},
    'speeding': {
        'label': "Over the speed limit", 'flags': ('speeding',),
        'delays': lambda offs: [0.0] * len(offs), 'speeding': True},
    'not_started': {
        'label': "Never started", 'flags': ('not_started', 'incomplete'),
        'delays': lambda offs: [0.0] * len(offs), 'no_positions': True},
    'late_deviation': {
        'label': "Late and off the route", 'flags': ('late', 'off_route'),
        'delays': _late, 'off_route': True},
}

# The demo set: twelve trips spread over the four lines, one scenario each. The deviation needs a stretch of
# several minutes, so it goes on the lines with long stretches.
DEMO_SET = [
    ('L1', 'punctual'), ('L1', 'within_tolerance'), ('L1', 'early'),
    ('L2', 'late'), ('L2', 'deviation'), ('L2', 'skipped_stop'),
    ('L3', 'punctual'), ('L3', 'incomplete_end'), ('L3', 'not_started'),
    ('L4', 'late_deviation'), ('L4', 'speeding'), ('L4', 'punctual'),
]


def side_step(a, b):
    """A displacement of about 500 m at a right angle to the way from `a` to `b` (latitude, longitude)."""
    d_lat, d_lon = b[0] - a[0], b[1] - a[1]
    length = (d_lat ** 2 + d_lon ** 2) ** 0.5 or 1.0
    return -d_lon / length * SIDE_STEP_DEG, d_lat / length * SIDE_STEP_DEG


def plan_minutes(route, speed_kmh=PLAN_SPEED_KMH):
    """Planned minutes from the first stop for each stop, from the distance along the line at an even speed."""
    stops = route.stop_ids
    offsets, covered = [0], 0.0
    for a, b in zip(stops, stops[1:]):
        covered += haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)
        offsets.append(max(int(round(covered / (speed_kmh * 1000.0 / 60.0))), offsets[-1] + 2))
    return offsets


class BusTripSimulator(models.AbstractModel):
    _name = 'bus.trip.simulator'
    _description = 'Trip simulator'

    @api.model
    def _ensure_plan(self, route):
        """Give the stops planned minutes when they have none (an even speed along the route)."""
        stops = route.stop_ids
        if len(stops) < 2 or any(stops.mapped('planned_offset_min')):
            return
        for stop, minutes in reversed(list(zip(stops, plan_minutes(route)))):    # last first: they never go back
            stop.planned_offset_min = minutes

    @api.model
    def _vehicle_for(self, route):
        Vehicle = self.env['bus.vehicle'].with_context(active_test=False)
        name = 'Sim %s' % route.code
        bus = Vehicle.search([('name', '=', name)], limit=1)
        if not bus:
            bus = Vehicle.create({'name': name, 'simulated': True, 'capacity': 40})
        bus.route_id = route
        return bus

    @api.model
    def _reset(self, bus):
        """A simulated bus carries no real state: the system ignores a position older than the last one, so each
        replay starts from a clean bus (the days of the simulated trips are not in order)."""
        open_alerts = self.env['bus.alert'].search([('vehicle_id', '=', bus.id), ('state', '=', 'open')])
        open_alerts._close(fields.Datetime.now())
        bus.write({'last_fix_time': False, 'current_stop_id': False, 'off_route_since': False})

    @api.model
    def _day_for(self, days_ago, route):
        """A local day that is over, on which the simulated bus of the route has no trip yet."""
        today = utc_to_local_date(fields.Datetime.now())
        day = today - timedelta(days=days_ago)
        bus = self._vehicle_for(route)
        while self.env['bus.trip'].search_count([
                ('vehicle_id', '=', bus.id), ('date', '=', day), ('simulated', '=', True)]):
            day -= timedelta(days=1)
        return day

    # ------------------------------------------------------------------
    @api.model
    def _simulate(self, route, scenario, day=None, days_ago=1):
        """Create a simulated trip of `route` and replay the scenario. Returns the trip."""
        spec = SCENARIOS.get(scenario)
        if not spec:
            raise UserError(_("Unknown scenario."))
        if len(route.stop_ids) < 2:
            raise UserError(_("The route needs at least two stops."))
        self._ensure_plan(route)
        bus = self._vehicle_for(route)
        self._reset(bus)
        day = day or self._day_for(days_ago, route)
        trip = self.env['bus.trip'].create({
            'vehicle_id': bus.id, 'route_id': route.id, 'planned_start': local_to_utc(day, START_LOCAL),
            'simulated': True, 'scenario': scenario, 'expected_flags': ','.join(sorted(spec['flags']))})
        if not spec.get('no_positions'):
            self._replay(trip, spec)
        # Close what the replay left open and report the late start, as the cron does for real trips.
        self.env['bus.trip']._cron_close_trips()
        return trip

    @api.model
    def _replay(self, trip, spec):
        bus = trip.vehicle_id
        lines = trip.stop_line_ids.sorted(lambda ln: (ln.sequence, ln.id))
        stops = [ln.stop_id for ln in lines]
        offsets = [ln.stop_id.planned_offset_min for ln in lines]
        delays = spec['delays'](offsets)
        n = len(stops)
        arrival = [ln.planned_time + timedelta(minutes=d) for ln, d in zip(lines, delays)]
        skip = {n // 2} if spec.get('skip') == 'middle' else set()
        last = n - 2 if spec.get('stop_before_end') else n - 1
        # the longest stretch carries the deviation
        durations = [(arrival[i + 1] - arrival[i]).total_seconds() for i in range(n - 1)]
        long_leg = max(range(n - 1), key=lambda i: durations[i]) if n > 1 else 0
        points = []                                        # (time, lat, lon, km/h)

        def add(when, lat, lon, kmh):
            points.append((when, lat, lon, kmh))

        for i in range(last + 1):
            stop = stops[i]
            ahead = stops[i + 1] if i + 1 < n else stops[i - 1]
            if i in skip:
                d_lat, d_lon = side_step((stop.latitude, stop.longitude), (ahead.latitude, ahead.longitude))
                add(arrival[i], stop.latitude + d_lat, stop.longitude + d_lon, 15.0)   # passes by, out of the radius
            else:
                add(arrival[i], stop.latitude, stop.longitude, 0.0)
                add(arrival[i] + timedelta(seconds=DWELL_S), stop.latitude, stop.longitude, 0.0)
            if i == last or i + 1 > last:
                break
            start = arrival[i] + timedelta(seconds=DWELL_S + 15)
            end = arrival[i + 1] - timedelta(seconds=15)
            seconds = (end - start).total_seconds()
            if seconds <= POSITION_EVERY_S:
                continue
            nxt = stops[i + 1]
            d_lat, d_lon = side_step((stop.latitude, stop.longitude), (nxt.latitude, nxt.longitude))
            distance = haversine_m(stop.latitude, stop.longitude, nxt.latitude, nxt.longitude)
            kmh = distance / 1000.0 / (seconds / 3600.0)
            if spec.get('speeding') and i == 0:
                kmh = 68.0
            count = int(seconds // POSITION_EVERY_S)
            for k in range(1, count):
                f = k / float(count)
                lat = stop.latitude + (nxt.latitude - stop.latitude) * f
                lon = stop.longitude + (nxt.longitude - stop.longitude) * f
                if spec.get('off_route') and i == long_leg and 0.1 < f < 0.9:
                    lat, lon = lat + d_lat, lon + d_lon                        # well beyond the corridor
                add(start + timedelta(seconds=seconds * f), lat, lon, kmh)
        for when, lat, lon, kmh in points:
            bus._apply_position({
                'fixTime': when.strftime('%Y-%m-%dT%H:%M:%SZ'), 'latitude': lat, 'longitude': lon,
                'speed': kmh / 1.852, 'course': 0.0})

    @api.model
    def _simulate_demo_set(self):
        """The twelve trips of the demo set (see DEMO_SET), on routes that exist by code."""
        trips = self.env['bus.trip']
        taken = {}
        for code, scenario in DEMO_SET:
            route = self.env['bus.route'].search([('code', '=', code)], limit=1)
            if not route:
                continue
            taken[code] = taken.get(code, 0) + 1
            trips |= self._simulate(route, scenario, days_ago=taken[code])
        return trips


class BusTripSimulate(models.TransientModel):
    _name = 'bus.trip.simulate'
    _description = 'Simulate trips'

    scenario = fields.Selection(
        [(key, spec['label']) for key, spec in SCENARIOS.items()], required=True, default='punctual')
    route_id = fields.Many2one('bus.route', string="Route", required=True, ondelete='cascade')

    def _open_trips(self, trips):
        return {
            'type': 'ir.actions.act_window', 'name': _("Simulated trips"), 'res_model': 'bus.trip',
            'view_mode': 'tree,form', 'domain': [('id', 'in', trips.ids)],
        }

    def action_simulate(self):
        self.ensure_one()
        return self._open_trips(self.env['bus.trip.simulator']._simulate(self.route_id, self.scenario))

    def action_demo_set(self):
        trips = self.env['bus.trip.simulator']._simulate_demo_set()
        if not trips:
            raise UserError(_("No route with the codes L1 to L4 exists: use the simulator on one of your routes."))
        return self._open_trips(trips)
