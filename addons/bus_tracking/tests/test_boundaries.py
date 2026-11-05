"""Black-box tests of the rules and the indicators: a valid input, an invalid one and the value on the limit."""
from datetime import date, datetime, timedelta
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import traccar_position
from .test_kpi import KpiCase
from .test_trips import MONDAY, TripCase


@tagged('post_install', '-at_install')
class TestAssignBoundaries(TripCase):

    def wizard(self, days):
        return self.env['bus.trip.assign'].create({
            'schedule_id': self.schedule.id, 'vehicle_id': self.bus.id,
            'date_from': MONDAY, 'date_to': MONDAY + timedelta(days=days)})

    def test_ninety_two_days_is_the_longest_period(self):
        self.wizard(92)

    def test_ninety_three_days_is_refused(self):
        with self.assertRaises(ValidationError):
            self.wizard(93)

    def test_one_day_period_is_valid(self):
        self.assertEqual(len(self.env['bus.trip'].search(self.wizard(0).action_assign()['domain'])), 1)

    def test_the_wizard_opens_with_the_schedule_and_its_bus(self):
        action = self.schedule.action_assign_wizard()
        self.assertEqual(action['res_model'], 'bus.trip.assign')
        self.assertEqual(action['context']['default_schedule_id'], self.schedule.id)
        self.assertEqual(action['context']['default_vehicle_id'], self.bus.id)

    def test_a_schedule_without_a_bus_makes_no_trips_and_no_error(self):
        self.schedule.vehicle_id = False
        self.assertFalse(self.schedule._generate_trips(MONDAY, MONDAY + timedelta(days=6)))

    def test_generating_twice_does_not_duplicate(self):
        first = self.schedule._generate_trips(MONDAY, MONDAY + timedelta(days=6))
        self.assertTrue(first)
        self.assertFalse(self.schedule._generate_trips(MONDAY, MONDAY + timedelta(days=6)))

    def test_a_trip_counts_its_stops(self):
        trip = self.trip()
        self.assertEqual(trip.stop_count, len(self.route.stop_ids))
        self.assertEqual(trip.stop_count, 3)

    def test_the_distance_of_a_trip_comes_from_its_route_unless_given(self):
        self.assertEqual(self.trip().distance_est_km, self.route.distance_km)
        given = self.trip(start_local=9.0, distance_est_km=1.5)
        self.assertEqual(given.distance_est_km, 1.5)


@tagged('post_install', '-at_install')
class TestAlertBoundaries(TripCase):

    def test_the_same_event_of_a_trip_is_written_once(self):
        trip = self.trip()
        when = datetime(2026, 10, 26, 12, 0)
        first = self.env['bus.alert']._trip_event(trip, 'late_start', when, delay_min=12.0)
        again = self.env['bus.alert']._trip_event(trip, 'late_start', when + timedelta(minutes=3), delay_min=15.0)
        self.assertEqual(first, again)
        self.assertEqual(first.delay_min, 12.0)

    def test_the_same_kind_on_another_stop_is_another_event(self):
        trip = self.trip()
        stops = trip.stop_line_ids.mapped('stop_id')
        when = datetime(2026, 10, 26, 12, 0)
        one = self.env['bus.alert']._trip_event(trip, 'late_arrival', when, stop_id=stops[0].id, delay_min=8.0)
        other = self.env['bus.alert']._trip_event(trip, 'late_arrival', when, stop_id=stops[1].id, delay_min=9.0)
        self.assertNotEqual(one, other)

    def test_every_kind_explains_itself_in_words(self):
        trip = self.trip()
        when = datetime(2026, 10, 26, 12, 0)
        facts = {
            'speeding': dict(max_speed=72.0, threshold=50.0), 'offline': {}, 'long_stop': {},
            'off_route': dict(distance_m=240.0), 'incomplete_trip': dict(threshold=2.0),
            'late_start': dict(delay_min=11.0),
        }
        for kind, values in facts.items():
            alert = self.env['bus.alert'].create(dict(
                values, vehicle_id=self.bus.id, kind=kind, start_time=when, end_time=when + timedelta(minutes=12),
                state='closed', trip_id=trip.id))
            self.assertTrue(alert.detail, kind)
            self.assertNotIn('%(', alert.detail, kind)
        self.assertIn('12', self.env['bus.alert'].search([('kind', '=', 'offline')], limit=1).detail)

    def test_an_open_alert_measures_its_duration_up_to_now(self):
        started = datetime.now() - timedelta(minutes=30)
        alert = self.env['bus.alert'].create({'vehicle_id': self.bus.id, 'kind': 'offline', 'start_time': started})
        self.assertAlmostEqual(alert.duration_minutes, 30.0, delta=1.0)


@tagged('post_install', '-at_install')
class TestPositionBoundaries(TripCase):

    def apply(self, **changes):
        position = traccar_position(7, '2026-10-26T12:00:00Z', -33.45, -70.66)
        position.update(changes)
        return self.bus._apply_position(position)

    def test_a_valid_position_is_stored(self):
        self.assertTrue(self.apply())

    def test_the_corners_of_the_earth_are_valid(self):
        for second, (lat, lon) in enumerate(((90.0, 180.0), (-90.0, -180.0)), start=1):
            self.assertTrue(self.apply(latitude=lat, longitude=lon, fixTime='2026-10-26T12:00:%02dZ' % second))

    def test_one_step_beyond_is_refused(self):
        for lat, lon in ((90.0001, 0.0), (-90.0001, 0.0), (0.0, 180.0001), (0.0, -180.0001)):
            with self.assertRaises(ValidationError, msg=str((lat, lon))):
                self.apply(latitude=lat, longitude=lon)

    def test_not_a_number_and_infinity_are_refused(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            with self.assertRaises(ValidationError):
                self.apply(latitude=value)
        with self.assertRaises(ValidationError):
            self.apply(longitude='north')

    def test_the_optional_figures_that_are_not_numbers_become_zero(self):
        record = self.apply(speed='fast', course='up', altitude='high')
        self.assertEqual((record.speed, record.course, record.altitude), (0.0, 0.0, 0.0))

    def test_a_position_without_time_or_coordinates_is_dropped_quietly(self):
        self.assertFalse(self.apply(fixTime=None))
        self.assertFalse(self.apply(latitude=None))


@tagged('post_install', '-at_install')
class TestIndicatorBoundaries(KpiCase):

    def test_the_period_accepts_dates_datetimes_and_text(self):
        day = date(2026, 10, 20)
        expected = (day, day + timedelta(days=3))
        self.assertEqual(self.kpi._period(day, day + timedelta(days=3)), expected)
        self.assertEqual(self.kpi._period(datetime(2026, 10, 20, 23, 59), datetime(2026, 10, 23, 0, 1)),
                         expected)
        self.assertEqual(self.kpi._period('2026-10-20', '2026-10-23'), expected)

    def test_a_reversed_period_is_put_in_order(self):
        self.assertEqual(self.kpi._period(date(2026, 10, 23), date(2026, 10, 20)),
                         (date(2026, 10, 20), date(2026, 10, 23)))

    def test_without_dates_it_is_the_last_thirty_days(self):
        first, last = self.kpi._period()
        self.assertEqual((last - first).days, 29)

    def test_an_unknown_scope_means_everything(self):
        self.assertEqual(self.kpi._params(scope='nonsense')['scope'], 'all')
        self.assertEqual(self.kpi._params(scope='real')['scope'], 'real')

    def test_a_period_without_trips_gives_no_figure_not_zero(self):
        far = self.kpi.compute(date_from=date(2020, 1, 1), date_to=date(2020, 1, 31))
        values = {m['code']: m['value'] for m in far['metrics']}
        for code in ('T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'):
            self.assertIsNone(values[code], code)

    def test_a_single_day_period_is_valid(self):
        result = self.kpi.compute(date_from=self.trip_a.date, date_to=self.trip_a.date)
        self.assertEqual(result['metrics'][0]['value'], 100.0)


@tagged('post_install', '-at_install')
class TestAuditSchedule(TripCase):

    def test_the_daily_audit_does_nothing_without_traccar(self):
        with patch('odoo.addons.bus_tracking.models.traccar_api.BusTraccarApi.is_configured', return_value=False):
            self.env['bus.sync.audit']._cron_run()
        self.assertFalse(self.env['bus.sync.audit'].search_count([]))

    def test_the_daily_audit_survives_a_failing_traccar(self):
        with patch('odoo.addons.bus_tracking.models.traccar_api.BusTraccarApi.is_configured', return_value=True), \
                patch('odoo.addons.bus_tracking.models.bus_quality.BusSyncAudit._run', side_effect=UserError('down')):
            self.env['bus.sync.audit']._cron_run()                      # must not raise
