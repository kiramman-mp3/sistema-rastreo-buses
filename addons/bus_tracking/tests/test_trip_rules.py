from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import traccar_position
from .test_trip_run import HOSPITAL, PAST, PLAZA, TERMINAL, RunCase


def alerts(trip, kind=None):
    domain = [('trip_id', '=', trip.id)] + ([('kind', '=', kind)] if kind else [])
    return trip.env['bus.alert'].search(domain)


@tagged('post_install', '-at_install')
class TestLateArrival(RunCase):

    def test_the_example_of_the_assignment(self):
        """A stop planned at 08:15 with a 5 minute tolerance and an arrival at 08:23: a late arrival of 8 minutes."""
        trip = self.trip(day=PAST, start_local=8.25)                 # the Terminal is at 08:15
        self.assertEqual(trip.stop_line_ids[0].planned_time.strftime('%H:%M'), '13:15')      # UTC-5
        self.at(8, TERMINAL, trip=trip)                              # 08:23
        line = self.line('Terminal', trip)
        self.assertEqual((line.status, line.delay_min), ('late', 8.0))
        alert = alerts(trip, 'late_arrival')
        self.assertEqual(len(alert), 1)
        self.assertEqual((alert.stop_id, alert.delay_min, alert.threshold), (self.stop['Terminal'], 8.0, 5.0))
        self.assertEqual(alert.state, 'closed')
        self.assertIn('8 min late at Terminal', alert.detail)

    def test_within_the_tolerance_there_is_no_alert(self):
        self.at(0, TERMINAL)
        self.at(15.0, PLAZA)                                         # planned +10: exactly 5 late
        self.assertFalse(alerts(self.trip_, 'late_arrival'))

    def test_each_late_stop_has_its_own_alert(self):
        self.at(0, TERMINAL)
        self.at(18, PLAZA)
        self.at(40, HOSPITAL)
        found = alerts(self.trip_, 'late_arrival')
        self.assertEqual(found.mapped('stop_id.name'), ['Hospital', 'Plaza'])
        self.assertEqual(sorted(found.mapped('delay_min')), [8.0, 15.0])

    def test_the_alert_belongs_to_the_bus_and_the_route(self):
        self.at(0, TERMINAL)
        self.at(18, PLAZA)
        alert = alerts(self.trip_, 'late_arrival')
        self.assertEqual((alert.vehicle_id, alert.route_id), (self.bus, self.route))

    def test_the_new_alerts_can_be_pushed_like_the_others(self):
        self.at(0, TERMINAL)
        self.at(18, PLAZA)
        self.env['bus.alert']._cron_push()
        self.assertTrue(alerts(self.trip_, 'late_arrival').notified)


@tagged('post_install', '-at_install')
class TestSkippedAndIncomplete(RunCase):

    def test_a_skipped_stop_and_an_incomplete_trip_are_reported(self):
        self.at(0, TERMINAL)
        self.at(25, HOSPITAL)
        trip = self.trip_
        self.assertEqual(alerts(trip, 'skipped_stop').stop_id, self.stop['Plaza'])
        incomplete = alerts(trip, 'incomplete_trip')
        self.assertEqual(incomplete.threshold, 1)
        self.assertIn('1 stops of the trip were not reached', incomplete.detail)
        self.assertIn('Did not stop at Plaza', alerts(trip, 'skipped_stop').detail)

    def test_a_complete_trip_reports_nothing_of_the_kind(self):
        self.at(0, TERMINAL)
        self.at(10, PLAZA)
        self.at(25, HOSPITAL)
        self.assertFalse(alerts(self.trip_, 'skipped_stop') | alerts(self.trip_, 'incomplete_trip'))

    def test_a_trip_that_never_started_is_one_incomplete_trip_not_one_alert_per_stop(self):
        self.env['bus.trip']._cron_close_trips()
        trip = self.trip_
        self.assertEqual(sorted(alerts(trip).mapped('kind')), ['incomplete_trip', 'late_start'])
        self.assertEqual(alerts(trip, 'incomplete_trip').threshold, 3)

    def test_closing_twice_does_not_repeat_the_alerts(self):
        self.at(0, TERMINAL)
        self.env['bus.trip']._cron_close_trips()
        count = len(alerts(self.trip_))
        self.env['bus.trip']._cron_close_trips()
        self.assertEqual(len(alerts(self.trip_)), count)


@tagged('post_install', '-at_install')
class TestLateStart(RunCase):

    def live_trip(self, minutes_ago):
        now = fields.Datetime.now().replace(microsecond=0)
        return self.env['bus.trip'].create({
            'vehicle_id': self.bus.id, 'route_id': self.route.id,
            'planned_start': now - timedelta(minutes=minutes_ago)})

    def test_a_trip_that_has_not_started_after_the_limit_is_reported_once(self):
        trip = self.live_trip(15)
        self.env['bus.trip']._cron_close_trips()
        late = alerts(trip, 'late_start')
        self.assertEqual((len(late), late.delay_min), (1, 10.0))
        self.assertTrue(trip.late_start_alerted)
        self.assertEqual(trip.state, 'planned')                      # still open: it may yet start
        self.env['bus.trip']._cron_close_trips()
        self.assertEqual(len(alerts(trip, 'late_start')), 1)

    def test_before_the_limit_there_is_nothing(self):
        trip = self.live_trip(5)
        self.env['bus.trip']._cron_close_trips()
        self.assertFalse(alerts(trip, 'late_start'))

    def test_a_trip_that_started_is_not_a_late_start(self):
        trip = self.live_trip(15)
        self.bus._apply_position(self.position_at(trip, 0))
        self.env['bus.trip']._cron_close_trips()
        self.assertEqual(trip.state, 'running')
        self.assertFalse(alerts(trip, 'late_start'))

    def test_the_alert_can_be_switched_off(self):
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.late_start_minutes', '0')
        trip = self.live_trip(15)
        self.env['bus.trip']._cron_close_trips()
        self.assertFalse(alerts(trip, 'late_start'))

    def position_at(self, trip, minutes):
        when = trip.planned_start + timedelta(minutes=minutes)
        return traccar_position(7, when.strftime('%Y-%m-%dT%H:%M:%SZ'), TERMINAL[0], TERMINAL[1], 0.0)


@tagged('post_install', '-at_install')
class TestDurationFlag(RunCase):

    def test_a_trip_much_longer_than_planned_is_flagged(self):
        self.at(0, TERMINAL)
        self.at(10, PLAZA)
        self.at(40, HOSPITAL)                                        # 40 minutes instead of 25: +60 %
        self.assertTrue(self.trip_.time_flag)

    def test_a_small_difference_is_not(self):
        self.at(0, TERMINAL)
        self.at(10, PLAZA)
        self.at(28, HOSPITAL)                                        # +12 %
        self.assertFalse(self.trip_.time_flag)

    def test_a_much_shorter_trip_is_flagged_too(self):
        self.at(0, TERMINAL)
        self.at(3, PLAZA)
        self.at(10, HOSPITAL)                                        # 10 instead of 25: -60 %
        self.assertTrue(self.trip_.time_flag)

    def test_the_limit_is_a_setting(self):
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.time_diff_pct', '80')
        self.at(0, TERMINAL)
        self.at(10, PLAZA)
        self.at(40, HOSPITAL)
        self.assertFalse(self.trip_.time_flag)
