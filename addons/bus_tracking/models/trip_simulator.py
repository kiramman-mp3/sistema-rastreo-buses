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
FAST_EVERY_S = 10              # on the speeding stretch the positions come more often, as a phone reports at speed
LONG_STOP_MIN = 25             # the long-stop scenario stands still this long, beyond the 20 minutes of its fine
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
        'delays': lambda offs: [0.0] * len(offs), 'speeding': 82.0},
    'speeding_tolerated': {
        'label': "Over the limit, inside the tolerance", 'flags': ('speeding',),
        'delays': lambda offs: [0.0] * len(offs), 'speeding': 62.0},
    'long_stop': {
        'label': "Long stop away from the stops", 'flags': ('late',),
        'delays': lambda offs: [0.0] * len(offs), 'long_stop': True},
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

# The fines demo: one trip per rule of a fine, plus the ones that must not become a fine (inside the tolerance) or
# that the system discards by itself (no GPS data on a trip that never started).
FINES_SET = ['speeding', 'speeding_tolerated', 'deviation', 'long_stop', 'skipped_stop', 'incomplete_end',
             'not_started']


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
    def _simulate(self, route, scenario, day=None, days_ago=1, driver=None):
        """Create a simulated trip of `route` and replay the scenario. Returns the trip. With a driver, the trip is
        theirs and so are the fines it proposes."""
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
            'simulated': True, 'scenario': scenario, 'expected_flags': ','.join(sorted(spec['flags'])),
            'driver_user_id': driver.id if driver else False})
        if not spec.get('no_positions'):
            self._replay(trip, spec)
        # Close what the replay left open and report the late start, as the cron does for real trips.
        self.env['bus.trip']._cron_close_trips(only=trip)
        # The fines of the trip are proposed now, not at the next run of the cron: the demonstration shows them at once.
        self.env['bus.fine']._detect_alerts(self.env['bus.alert'].search([
            ('vehicle_id', '=', bus.id), ('state', '=', 'closed'), ('fine_checked', '=', False)], order='id'))
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
        # the longest stretch carries the speeding run, the deviation and the long stop
        durations = [(arrival[i + 1] - arrival[i]).total_seconds() for i in range(n - 1)]
        long_leg = max(range(n - 1), key=lambda i: durations[i]) if n > 1 else 0
        if spec.get('long_stop'):
            # the bus stands still in the middle of the stretch: every stop after it is reached that much later
            arrival = arrival[:long_leg + 1] + [t + timedelta(minutes=LONG_STOP_MIN) for t in arrival[long_leg + 1:]]
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
            stand = LONG_STOP_MIN * 60.0 if spec.get('long_stop') and i == long_leg else 0.0
            driving = max(seconds - stand, 1.0)
            kmh = distance / 1000.0 / (driving / 3600.0)
            every = POSITION_EVERY_S
            if spec.get('speeding') and i == long_leg:
                kmh, every = spec['speeding'], FAST_EVERY_S
            count = max(int(driving // every), 4 if stand else 0)
            halted = False
            for k in range(1, count):
                f = k / float(count)
                if stand and f >= 0.5 and not halted:
                    # half way, the bus stands still away from any stop, reporting every minute
                    halted = True
                    lat, lon = self._place(stop, nxt, 0.5, None)
                    halt = start + timedelta(seconds=driving * 0.5)
                    for minute in range(int(stand // 60)):
                        add(halt + timedelta(seconds=minute * 60), lat, lon, 0.0)
                offset = (d_lat, d_lon) if spec.get('off_route') and i == long_leg else None
                lat, lon = self._place(stop, nxt, f, offset)
                add(start + timedelta(seconds=driving * f + (stand if halted else 0.0)), lat, lon, kmh)
        for when, lat, lon, kmh in points:
            bus._apply_position({
                'fixTime': when.strftime('%Y-%m-%dT%H:%M:%SZ'), 'latitude': lat, 'longitude': lon,
                'speed': kmh / 1.852, 'course': 0.0})

    @api.model
    def _place(self, stop, nxt, f, step):
        """A point at fraction f of the way between two stops; with a side step, pushed off the route in the middle
        of the way (well beyond the corridor)."""
        lat = stop.latitude + (nxt.latitude - stop.latitude) * f
        lon = stop.longitude + (nxt.longitude - stop.longitude) * f
        if step and 0.1 < f < 0.9:
            lat, lon = lat + step[0], lon + step[1]
        return lat, lon

    @api.model
    def _off_route_seconds(self, route):
        """How long the deviation scenario keeps the bus off the line on the longest stretch of a route: the same
        sampling as `_replay`, one position a minute pushed aside between 10 % and 90 % of the way."""
        self._ensure_plan(route)
        offsets = [s.planned_offset_min for s in route.stop_ids.sorted(lambda s: (s.sequence, s.id))]
        longest = max((b - a for a, b in zip(offsets, offsets[1:])), default=0)
        driving = longest * 60.0 - DWELL_S - 30
        count = int(driving // POSITION_EVERY_S)
        aside = [k for k in range(1, count) if 0.1 < k / float(count) < 0.9]
        return driving * (aside[-1] - aside[0]) / count if len(aside) > 1 else 0.0

    @api.model
    def _simulate_fines_set(self, route, driver=None):
        """One simulated trip per scenario of FINES_SET on a route, each on its own past day.

        The deviation and the speeding run need a stretch of several minutes: on a route of short stretches they
        would leave no alert and their fines would be missing without a word, so such a route is refused and the
        routes that fit are named."""
        needed = self.env['bus.alert']._param('off_route_minutes', 3) * 60
        if self._off_route_seconds(route) < needed:
            fit = self.env['bus.route'].search([('id', '!=', route.id)]).filtered(
                lambda r: len(r.stop_ids) > 1 and self._off_route_seconds(r) >= needed)
            raise UserError(_("The stretches of %(route)s are too short to show a deviation of %(minutes)s minutes "
                              "and a sustained speeding run. Choose a route with a longer stretch: %(routes)s.",
                              route=route.display_name, minutes=needed // 60,
                              routes=', '.join(fit.mapped('display_name')) or _("none")))
        trips = self.env['bus.trip']
        for days_ago, scenario in enumerate(FINES_SET, start=1):
            trips |= self._simulate(route, scenario, days_ago=days_ago, driver=driver)
        return trips

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
    driver_user_id = fields.Many2one(
        'res.users', string="Driver", ondelete='cascade',
        domain=lambda self: [('groups_id', 'in', self.env.ref('bus_tracking.group_bus_driver').ids)],
        help="The driver the simulated trips are given to, so their fines have someone to be proposed to. Without "
             "one, the fines are discarded by the system: nobody drove.")

    def _open_trips(self, trips):
        return {
            'type': 'ir.actions.act_window', 'name': _("Simulated trips"), 'res_model': 'bus.trip',
            'view_mode': 'tree,form', 'domain': [('id', 'in', trips.ids)],
        }

    def action_simulate(self):
        self.ensure_one()
        # Replaying a trip writes positions, arrivals and alerts, which belong to the system: only managers open this
        # wizard (its access rights), and it runs as the system.
        trips = self.env['bus.trip.simulator'].sudo()._simulate(self.route_id.sudo(), self.scenario,
                                                                driver=self.driver_user_id.sudo())
        return self._open_trips(trips)

    def action_fines_set(self):
        self.ensure_one()
        trips = self.env['bus.trip.simulator'].sudo()._simulate_fines_set(self.route_id.sudo(),
                                                                          driver=self.driver_user_id.sudo())
        return {
            'type': 'ir.actions.act_window', 'name': _("Fines of the simulated trips"), 'res_model': 'bus.fine',
            'view_mode': 'kanban,tree,form', 'domain': [('trip_id', 'in', trips.ids)],
        }

    def action_demo_set(self):
        trips = self.env['bus.trip.simulator'].sudo()._simulate_demo_set()
        if not trips:
            raise UserError(_("No route with the codes L1 to L4 exists: use the simulator on one of your routes."))
        return self._open_trips(trips)
