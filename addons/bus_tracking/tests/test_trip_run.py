from datetime import date, timedelta

from odoo import fields
from odoo.tests import tagged

from .common import traccar_position
from .test_trips import TripCase

PAST = date(2026, 10, 26)                      # a Monday that is over: its trips can be closed by the cron
TERMINAL = (-33.4500, -70.6600)
PLAZA = (-33.4540, -70.6500)
HOSPITAL = (-33.4600, -70.6400)
BETWEEN = (-33.4520, -70.6550)                 # on the line between the Terminal and the Plaza
FAR = (-33.4520, -70.6200)                     # about 3 km east of the line


class RunCase(TripCase):

    def setUp(self):
        super().setUp()
        self.trip_ = self.trip(day=PAST)

    def at(self, minutes, place, knots=0.0, trip=None):
        """A position `minutes` after the planned start of the trip."""
        when = (trip or self.trip_).planned_start + timedelta(minutes=minutes)
        self.bus._apply_position(traccar_position(
            7, when.strftime('%Y-%m-%dT%H:%M:%SZ'), place[0], place[1], knots))
        return when

    def line(self, name, trip=None):
        return (trip or self.trip_).stop_line_ids.filtered(lambda ln: ln.stop_id.name == name)


@tagged('post_install', '-at_install')
class TestTripRun(RunCase):

    def test_a_punctual_trip_is_done_with_every_stop_on_time(self):
        self.at(0, TERMINAL)
        self.at(3, BETWEEN, 10)
        self.at(10, PLAZA)
        self.at(25, HOSPITAL)
        trip = self.trip_
        self.assertEqual(trip.state, 'done')
        self.assertEqual(trip.stop_line_ids.mapped('status'), ['on_time'] * 3)
        self.assertEqual((trip.stops_visited, trip.stops_late, trip.stops_skipped), (3, 0, 0))
        self.assertEqual(trip.real_start, trip.planned_start)
        self.assertEqual(trip.real_end, trip.planned_start + timedelta(minutes=25))
        self.assertAlmostEqual(trip.duration_real_min, 25.0)
        self.assertAlmostEqual(trip.duration_diff_pct, 0.0)
        self.assertEqual(trip.delay_max_min, 0.0)

    def test_what_was_driven_is_measured_against_the_route(self):
        self.at(0, TERMINAL)
        self.at(5, BETWEEN, 10)
        self.at(10, PLAZA)
        self.at(25, HOSPITAL)
        trip = self.trip_
        self.assertGreater(trip.distance_real_km, 1.5)
        self.assertAlmostEqual(trip.distance_real_km, trip.distance_est_km, delta=0.4)
        self.assertEqual(trip.distance_est_km, self.route.distance_km)
        self.assertAlmostEqual(trip.corridor_pct, 100.0)
        self.assertLess(trip.deviation_max_m, 150)

    def test_a_position_far_from_the_line_shows_in_the_deviation(self):
        self.at(0, TERMINAL)
        self.at(4, FAR, 10)
        self.at(10, PLAZA)
        self.at(25, HOSPITAL)
        trip = self.trip_
        self.assertGreater(trip.deviation_max_m, 1000)
        self.assertLess(trip.corridor_pct, 100.0)

    def test_late_arrivals_are_measured_in_minutes(self):
        self.at(0, TERMINAL)
        self.at(18, PLAZA)                              # planned +10: 8 minutes late
        self.at(40, HOSPITAL)                           # planned +25: 15 minutes late
        trip = self.trip_
        self.assertEqual(trip.stop_line_ids.mapped('status'), ['on_time', 'late', 'late'])
        self.assertAlmostEqual(self.line('Plaza').delay_min, 8.0)
        self.assertEqual((trip.stops_late, trip.state), (2, 'done'))
        self.assertAlmostEqual(trip.delay_avg_min, 11.5)
        self.assertAlmostEqual(trip.delay_max_min, 15.0)
        self.assertAlmostEqual(trip.delay_end_min, 15.0)
        self.assertAlmostEqual(trip.duration_diff_pct, (40 - 25) / 25.0 * 100)

    def test_the_tolerance_limit_is_exact(self):
        """08:15 planned with 5 minutes of tolerance: 08:20:00 is on time, 08:20:01 is late (and 08:23 is 8 late)."""
        self.at(0, TERMINAL)
        self.at(15.0, PLAZA)                            # planned +10 = exactly 5 minutes late
        self.assertEqual(self.line('Plaza').status, 'on_time')
        second = self.trip(day=PAST, start_local=9.0)
        self.at(0, TERMINAL, trip=second)
        self.at(10 + 5 + 1 / 60.0, PLAZA, trip=second)  # 5 minutes and 1 second
        self.assertEqual(self.line('Plaza', second).status, 'late')

    def test_an_early_arrival_is_marked_early_beyond_the_tolerance(self):
        self.at(0, TERMINAL)
        self.at(3, PLAZA)                               # planned +10: 7 minutes early
        self.assertEqual(self.line('Plaza').status, 'early')
        self.assertAlmostEqual(self.line('Plaza').delay_min, -7.0)

    def test_the_tolerance_is_a_setting(self):
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.punctuality_tolerance_min', '10')
        self.at(0, TERMINAL)
        self.at(18, PLAZA)                              # 8 late: inside a 10 minute tolerance
        self.assertEqual(self.line('Plaza').status, 'on_time')

    def test_a_skipped_stop_makes_the_trip_incomplete(self):
        self.at(0, TERMINAL)
        self.at(25, HOSPITAL)                           # never entered the Plaza
        trip = self.trip_
        self.assertEqual(trip.state, 'incomplete')
        self.assertEqual(self.line('Plaza').status, 'skipped')
        self.assertEqual((trip.stops_visited, trip.stops_skipped), (2, 1))

    def test_an_arrival_outside_the_window_belongs_to_no_trip(self):
        self.at(180, TERMINAL)
        self.assertEqual(self.trip_.state, 'planned')
        self.assertFalse(self.trip_.stop_line_ids.filtered('actual_time'))

    def test_a_second_arrival_at_a_stop_keeps_the_first_time(self):
        self.at(0, TERMINAL)
        self.at(2, BETWEEN, 10)
        self.at(4, TERMINAL)
        self.assertEqual(self.line('Terminal').actual_time, self.trip_.planned_start)

    def test_the_arrival_goes_to_the_closest_of_two_consecutive_trips(self):
        second = self.trip(day=PAST, start_local=7.25 + 25 / 60.0)      # starts when the first one ends
        when = self.at(25.5, TERMINAL, trip=self.trip_)                   # 07:40:30: much closer to the second
        self.assertEqual(second.state, 'running')
        self.assertEqual(self.line('Terminal', second).actual_time, when)
        self.assertEqual(self.trip_.state, 'planned')


@tagged('post_install', '-at_install')
class TestTripClosing(RunCase):

    def test_the_cron_closes_a_trip_that_never_started(self):
        self.env['bus.trip']._cron_close_trips()
        trip = self.trip_
        self.assertEqual(trip.state, 'incomplete')
        self.assertEqual(set(trip.stop_line_ids.mapped('status')), {'skipped'})
        self.assertFalse(trip.real_end)

    def test_the_cron_closes_a_trip_left_half_way(self):
        self.at(0, TERMINAL)
        self.at(10, PLAZA)
        self.env['bus.trip']._cron_close_trips()
        trip = self.trip_
        self.assertEqual(trip.state, 'incomplete')
        self.assertEqual(trip.stop_line_ids.mapped('status'), ['on_time', 'on_time', 'skipped'])
        self.assertEqual(trip.real_end, trip.planned_start + timedelta(minutes=10))

    def test_the_cron_leaves_alone_a_trip_whose_time_is_not_over(self):
        now = fields.Datetime.now().replace(microsecond=0)
        live = self.env['bus.trip'].create({
            'vehicle_id': self.bus.id, 'route_id': self.route.id, 'planned_start': now - timedelta(minutes=5)})
        self.env['bus.trip']._cron_close_trips()
        self.assertEqual(live.state, 'planned')

    def test_a_closed_trip_is_not_closed_again(self):
        self.at(0, TERMINAL)
        self.at(10, PLAZA)
        self.at(25, HOSPITAL)
        done_at = self.trip_.real_end
        self.env['bus.trip']._cron_close_trips()
        self.assertEqual((self.trip_.state, self.trip_.real_end), ('done', done_at))


@tagged('post_install', '-at_install')
class TestTripEvents(RunCase):

    def test_an_alert_belongs_to_the_trip_the_bus_was_on(self):
        self.at(0, TERMINAL)
        self.at(5, BETWEEN, 60.0)                       # about 111 km/h: speeding
        alert = self.env['bus.alert'].search([('vehicle_id', '=', self.bus.id), ('kind', '=', 'speeding')])
        self.assertEqual(alert.trip_id, self.trip_)
        self.assertEqual(self.trip_.alert_count, 1)

    def test_an_alert_outside_any_trip_has_none(self):
        when = self.trip_.planned_start + timedelta(hours=10)
        self.bus._apply_position(traccar_position(7, when.strftime('%Y-%m-%dT%H:%M:%SZ'), *BETWEEN, 60.0))
        alert = self.env['bus.alert'].search([('vehicle_id', '=', self.bus.id), ('kind', '=', 'speeding')])
        self.assertFalse(alert.trip_id)

    def test_an_incident_belongs_to_the_trip_too(self):
        user = self.env['res.users'].create({'name': 'Chofer', 'login': 'chofer-trip'})
        shift = self.env['bus.shift'].create({
            'user_id': user.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id,
            'start': self.trip_.planned_start})
        incident = self.env['bus.incident'].create({
            'shift_id': shift.id, 'vehicle_id': self.bus.id, 'kind': 'traffic',
            'reported_at': self.trip_.planned_start + timedelta(minutes=8)})
        self.assertEqual(incident.trip_id, self.trip_)
        self.assertEqual(self.trip_.incident_count, 1)
