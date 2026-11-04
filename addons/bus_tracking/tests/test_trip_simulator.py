import json

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, tagged

from ..controllers.portal import BusPortal
from ..models.trip_simulator import DEMO_SET, SCENARIOS, plan_minutes
from .test_trips import TripCase


def simulator(env):
    return env['bus.trip.simulator']


@tagged('post_install', '-at_install')
class TestScenarios(TripCase):

    def test_every_scenario_triggers_exactly_what_it_expects(self):
        """The detection is measured: what the rules found on each simulated trip equals what the scenario meant."""
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                days_ago = 1 + list(SCENARIOS).index(scenario)
                trip = simulator(self.env)._simulate(self.route, scenario, days_ago=days_ago)
                self.assertTrue(trip.simulated)
                self.assertEqual(trip.scenario, scenario)
                self.assertIn(trip.state, ('done', 'incomplete'))
                expected = ','.join(sorted(SCENARIOS[scenario]['flags']))
                self.assertEqual(trip.detected_flags, expected, trip.detected_flags)
                self.assertTrue(trip.detection_ok)

    def test_a_punctual_trip_is_done_with_nothing_to_report(self):
        trip = simulator(self.env)._simulate(self.route, 'punctual')
        self.assertEqual((trip.state, trip.stops_visited, trip.stops_late, trip.stops_skipped), ('done', 3, 0, 0))
        self.assertFalse(trip.alert_ids)

    def test_the_late_trip_shows_its_delay(self):
        trip = simulator(self.env)._simulate(self.route, 'late')
        self.assertGreater(trip.delay_end_min, 5)
        self.assertGreater(trip.duration_diff_pct, 0)
        late = trip.alert_ids.filtered(lambda a: a.kind == 'late_arrival')
        self.assertEqual(set(late.mapped('stop_id.name')), {'Plaza', 'Hospital'})

    def test_the_deviation_is_measured(self):
        trip = simulator(self.env)._simulate(self.route, 'deviation')
        self.assertGreater(trip.deviation_max_m, 400)
        self.assertLess(trip.corridor_pct, 100)
        self.assertTrue(trip.alert_ids.filtered(lambda a: a.kind == 'off_route'))

    def test_a_trip_that_never_started_has_no_positions(self):
        trip = simulator(self.env)._simulate(self.route, 'not_started')
        self.assertFalse(self.env['bus.position'].search([('vehicle_id', '=', trip.vehicle_id.id)]))
        self.assertEqual(sorted(trip.alert_ids.mapped('kind')), ['incomplete_trip', 'late_start'])

    def test_a_wrong_expectation_is_not_hidden(self):
        trip = simulator(self.env)._simulate(self.route, 'punctual')
        trip.expected_flags = 'late'
        self.assertFalse(trip.detection_ok)

    def test_the_same_route_can_be_simulated_again_without_clashing(self):
        first = simulator(self.env)._simulate(self.route, 'punctual')
        second = simulator(self.env)._simulate(self.route, 'punctual')
        self.assertNotEqual(first.date, second.date)
        self.assertEqual(first.vehicle_id, second.vehicle_id)

    def test_unknown_scenarios_and_routes_without_stops_are_refused(self):
        with self.assertRaises(UserError):
            simulator(self.env)._simulate(self.route, 'nonsense')
        bare = self.env['bus.route'].create({'name': 'Vacia', 'code': 'V1'})
        with self.assertRaises(UserError):
            simulator(self.env)._simulate(bare, 'punctual')


@tagged('post_install', '-at_install')
class TestPlan(TransactionCase):

    def make(self, code, offsets=None):
        return self.env['bus.route'].create({
            'name': 'Linea ' + code, 'code': code,
            'stop_ids': [(0, 0, {'sequence': i, 'name': '%s-%d' % (code, i), 'latitude': -1.2 - i * 0.012,
                                 'longitude': -78.6, 'radius': 60, 'planned_offset_min': (offsets or [0] * 4)[i]})
                         for i in range(4)]})

    def test_the_planned_minutes_follow_the_distance_and_never_stall(self):
        route = self.make('P1')
        offsets = plan_minutes(route)
        self.assertEqual(offsets[0], 0)
        self.assertTrue(all(b - a >= 2 for a, b in zip(offsets, offsets[1:])))

    def test_a_plan_that_exists_is_not_overwritten(self):
        route = self.make('P2', offsets=[0, 5, 9, 14])
        simulator(self.env)._ensure_plan(route)
        self.assertEqual(route.stop_ids.mapped('planned_offset_min'), [0, 5, 9, 14])

    def test_a_route_without_a_plan_gets_one(self):
        route = self.make('P3')
        simulator(self.env)._ensure_plan(route)
        self.assertGreater(route.stop_ids[-1].planned_offset_min, 0)


@tagged('post_install', '-at_install')
class TestDemoSet(TransactionCase):

    def setUp(self):
        super().setUp()
        for code in ('L1', 'L2', 'L3', 'L4'):
            self.env['bus.route'].create({
                'name': 'Linea ' + code, 'code': code,
                # stretches of about 5 km: long enough for a deviation of several minutes
                'stop_ids': [(0, 0, {'sequence': i, 'name': '%s-%d' % (code, i), 'latitude': -1.2 - i * 0.05,
                                     'longitude': -78.6 + int(code[1]) * 0.05, 'radius': 60}) for i in range(4)]})

    def test_the_demo_set_has_twelve_simulated_trips_and_all_are_detected(self):
        trips = simulator(self.env)._simulate_demo_set()
        self.assertEqual(len(trips), len(DEMO_SET))
        self.assertGreaterEqual(len(trips), 10)                    # the assignment asks for at least ten
        self.assertEqual(set(trips.mapped('simulated')), {True})
        self.assertEqual(len(set(trips.mapped('route_id'))), 4)
        self.assertEqual(len(set(trips.mapped('scenario'))), 10)
        wrong = trips.filtered(lambda t: not t.detection_ok)
        self.assertFalse(wrong, wrong.mapped('scenario'))

    def test_the_wizard_runs_one_scenario_or_the_whole_set(self):
        wizard = self.env['bus.trip.simulate'].create({
            'route_id': self.env['bus.route'].search([('code', '=', 'L1')]).id, 'scenario': 'early'})
        action = wizard.action_simulate()
        self.assertEqual(self.env['bus.trip'].search(action['domain']).scenario, 'early')
        action = wizard.action_demo_set()
        self.assertEqual(len(self.env['bus.trip'].search(action['domain'])), len(DEMO_SET))


@tagged('post_install', '-at_install')
class TestDemoSetWithoutLines(TransactionCase):

    def test_the_wizard_refuses_the_demo_set_when_no_line_has_a_known_code(self):
        route = self.env['bus.route'].create({
            'name': 'Otra', 'code': 'Z9',
            'stop_ids': [(0, 0, {'name': 'a', 'latitude': -1.2, 'longitude': -78.6}),
                         (0, 0, {'name': 'b', 'latitude': -1.3, 'longitude': -78.6})]})
        wizard = self.env['bus.trip.simulate'].create({'route_id': route.id})
        with self.assertRaises(UserError):
            wizard.action_demo_set()


@tagged('post_install', '-at_install')
class TestSimulatedBusesStayHidden(HttpCase):

    def setUp(self):
        super().setUp()
        self.route = self.env['bus.route'].create({
            'name': 'Linea', 'code': 'S1',
            'stop_ids': [(0, 0, {'sequence': i, 'name': 'S%d' % i, 'latitude': -1.2 - i * 0.012,
                                 'longitude': -78.6, 'radius': 60}) for i in range(3)]})
        self.fake = self.env['bus.vehicle'].create({
            'name': 'Sim S1', 'simulated': True, 'route_id': self.route.id,
            'last_fix_time': fields.Datetime.now(), 'last_latitude': -1.2, 'last_longitude': -78.6})
        self.real = self.env['bus.vehicle'].create({
            'name': 'Bus real', 'route_id': self.route.id,
            'last_fix_time': fields.Datetime.now(), 'last_latitude': -1.21, 'last_longitude': -78.6})

    def test_the_live_map_does_not_show_a_simulated_bus(self):
        self.authenticate('admin', 'admin')
        resp = self.url_open('/bus_tracking/live', data=json.dumps(
            {'jsonrpc': '2.0', 'method': 'call', 'params': {}}), headers={'Content-Type': 'application/json'})
        self.assertEqual([v['name'] for v in resp.json()['result']['vehicles']], ['Bus real'])

    def test_the_public_pages_do_not_show_a_simulated_bus(self):
        self.assertEqual(BusPortal._fresh_buses(self.route), self.real)
