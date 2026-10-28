from datetime import datetime, timedelta

from odoo.tests import tagged

from .common import BusCase, traccar_position

# the three stops of the test route are about 1 km apart: Terminal, Plaza, Hospital
TERMINAL = (-33.4500, -70.6600)
PLAZA = (-33.4540, -70.6500)
HOSPITAL = (-33.4600, -70.6400)
BETWEEN = (-33.4520, -70.6550)
BASE = datetime(2026, 10, 27, 12, 0, 0)


@tagged('post_install', '-at_install')
class TestRuns(BusCase):

    def go(self, minute, place):
        when = BASE + timedelta(minutes=minute)
        self.bus._apply_position(traccar_position(7, when.strftime('%Y-%m-%dT%H:%M:%SZ'), place[0], place[1], 10.0))
        return when

    def runs(self):
        return self.env['bus.run'].search([('vehicle_id', '=', self.bus.id)], order='departure')

    def test_leaving_one_end_and_reaching_the_other_writes_a_trip(self):
        self.go(0, TERMINAL)
        left = self.go(2, BETWEEN)
        run = self.runs()
        self.assertEqual((run.state, run.departure, run.origin_stop_id), ('running', left, self.stop['Terminal']))
        arrived = self.go(20, HOSPITAL)
        self.assertEqual((run.state, run.arrival, run.destination_stop_id), ('done', arrived, self.stop['Hospital']))
        self.assertAlmostEqual(run.duration_minutes, 18.0)

    def test_the_way_back_is_another_trip(self):
        self.go(0, TERMINAL)
        self.go(2, BETWEEN)
        self.go(20, HOSPITAL)
        self.go(30, BETWEEN)
        self.go(50, TERMINAL)
        runs = self.runs()
        self.assertEqual(len(runs), 2)
        self.assertEqual((runs[1].origin_stop_id, runs[1].destination_stop_id),
                         (self.stop['Hospital'], self.stop['Terminal']))

    def test_passing_the_middle_stop_does_not_end_the_trip(self):
        self.go(0, TERMINAL)
        self.go(2, BETWEEN)
        self.go(10, PLAZA)
        self.go(12, BETWEEN)
        self.assertEqual(self.runs().state, 'running')
        self.assertEqual(len(self.runs()), 1)

    def test_coming_back_to_the_start_discards_the_trip(self):
        self.go(0, TERMINAL)
        self.go(2, BETWEEN)
        self.go(8, TERMINAL)
        self.assertFalse(self.runs())

    def test_a_bus_that_starts_in_the_middle_makes_no_trip_until_it_reaches_an_end(self):
        self.go(0, BETWEEN)
        self.go(5, PLAZA)
        self.go(10, HOSPITAL)
        self.assertFalse(self.runs())

    def test_a_route_with_one_stop_makes_no_trips(self):
        single = self.env['bus.route'].create({
            'name': 'Corta', 'code': 'C1',
            'stop_ids': [(0, 0, {'name': 'Unica', 'latitude': TERMINAL[0], 'longitude': TERMINAL[1], 'radius': 80})]})
        self.bus.route_id = single
        self.go(0, TERMINAL)
        self.go(2, BETWEEN)
        self.assertFalse(self.runs())

    def test_changing_the_route_drops_the_open_trip(self):
        self.go(0, TERMINAL)
        self.go(2, BETWEEN)
        other = self.env['bus.route'].create({
            'name': 'Otra', 'code': 'O1', 'stop_ids': [
                (0, 0, {'name': 'A', 'latitude': HOSPITAL[0], 'longitude': HOSPITAL[1], 'radius': 80}),
                (0, 0, {'name': 'B', 'latitude': -33.47, 'longitude': -70.63, 'radius': 80})]})
        self.bus.route_id = other
        self.go(5, HOSPITAL)
        self.assertFalse(self.runs().filtered(lambda r: r.route_id == self.route))

    def test_trips_left_open_for_many_hours_are_discarded(self):
        self.go(0, TERMINAL)
        self.go(2, BETWEEN)
        self.runs().departure = datetime(2020, 1, 1)
        self.env['bus.run']._cron_discard_stale()
        self.assertFalse(self.runs())
