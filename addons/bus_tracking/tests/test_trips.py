from datetime import date, datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from ..models.bus_trip import hours_text, local_to_utc, utc_to_local_date
from .common import BusCase

MONDAY = date(2026, 11, 9)
SATURDAY = date(2026, 11, 14)
# planned minutes of the three stops of the test route (Terminal, Plaza, Hospital)
OFFSETS = {'Terminal': 0, 'Plaza': 10, 'Hospital': 25}


class TripCase(BusCase):
    """The test route with planned minutes on its stops, so trips can be scheduled on it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # last stop first: the minutes may never go back along the route, even while they are being set
        for name, minutes in reversed(list(OFFSETS.items())):
            cls.stop[name].planned_offset_min = minutes
        cls.schedule = cls.env['bus.route.schedule'].create({
            'route_id': cls.route.id, 'departure_time': 7.25, 'vehicle_id': cls.bus.id})

    def trip(self, start_local=7.25, day=MONDAY, bus=None, route=None, **extra):
        return self.env['bus.trip'].create(dict({
            'vehicle_id': (bus or self.bus).id, 'route_id': (route or self.route).id,
            'planned_start': local_to_utc(day, start_local)}, **extra))


@tagged('post_install', '-at_install')
class TestTimes(TripCase):

    def test_local_time_is_stored_in_utc(self):
        # Ecuador is UTC-5 all year: 07:15 local is 12:15 UTC
        self.assertEqual(local_to_utc(MONDAY, 7.25), datetime(2026, 11, 9, 12, 15))
        self.assertEqual(utc_to_local_date(datetime(2026, 11, 10, 3, 0)), date(2026, 11, 9))
        self.assertEqual(hours_text(7.25), '07:15')
        self.assertEqual(hours_text(23.999), '00:00')

    def test_the_schedule_knows_its_name_and_arrival(self):
        self.assertEqual(self.schedule.name, 'L1 07:15')
        self.assertAlmostEqual(self.schedule.arrival_time, 7.25 + 25 / 60.0)


@tagged('post_install', '-at_install')
class TestRouteDistanceAndOffsets(TripCase):

    def test_distance_comes_from_the_line_of_the_route(self):
        self.assertGreater(self.route.distance_km, 1.0)
        before = self.route.distance_km
        self.route.track_json = '[[-33.45,-70.66],[-33.50,-70.60]]'
        self.assertNotEqual(self.route.distance_km, before)

    def test_origin_and_destination_are_the_ends(self):
        self.assertEqual(self.route.origin_stop_id, self.stop['Terminal'])
        self.assertEqual(self.route.destination_stop_id, self.stop['Hospital'])

    def test_planned_minutes_never_go_back(self):
        with self.assertRaises(ValidationError):
            self.stop['Plaza'].planned_offset_min = 30     # later than the Hospital (25)
        with self.assertRaises(ValidationError):
            self.stop['Plaza'].planned_offset_min = -1

    def test_equal_minutes_are_allowed(self):
        self.stop['Plaza'].planned_offset_min = 25
        self.assertEqual(self.stop['Plaza'].planned_offset_min, 25)


@tagged('post_install', '-at_install')
class TestTripCreation(TripCase):

    def test_a_trip_has_its_planned_window_and_a_line_per_stop(self):
        trip = self.trip()
        self.assertEqual(trip.planned_start, datetime(2026, 11, 9, 12, 15))
        self.assertEqual(trip.planned_end, datetime(2026, 11, 9, 12, 40))
        self.assertEqual(trip.date, MONDAY)
        self.assertEqual(trip.state, 'planned')
        self.assertEqual(trip.stop_line_ids.mapped('stop_id.name'), ['Terminal', 'Plaza', 'Hospital'])
        self.assertEqual(trip.stop_line_ids.mapped('planned_time'),
                         [trip.planned_start + timedelta(minutes=m) for m in (0, 10, 25)])
        self.assertEqual(set(trip.stop_line_ids.mapped('status')), {'pending'})
        self.assertIn('L1', trip.name)

    def test_a_route_without_planned_minutes_cannot_be_scheduled(self):
        bare = self.env['bus.route'].create({
            'name': 'Sin horario', 'code': 'S1',
            'stop_ids': [(0, 0, {'name': n, 'latitude': -33.4 - i / 100, 'longitude': -70.6})
                         for i, n in enumerate(('A', 'B'))]})
        with self.assertRaises(ValidationError):
            self.trip(route=bare)

    def test_a_trip_that_crosses_midnight_keeps_its_local_date(self):
        trip = self.trip(start_local=23.75)             # 23:45 local, ends 00:10 local
        self.assertEqual(trip.date, MONDAY)
        self.assertEqual(trip.planned_end - trip.planned_start, timedelta(minutes=25))
        self.assertEqual(utc_to_local_date(trip.planned_end), MONDAY + timedelta(days=1))


@tagged('post_install', '-at_install')
class TestAssignment(TripCase):

    def other_route(self):
        route = self.env['bus.route'].create({
            'name': 'Linea Norte', 'code': 'L2',
            'stop_ids': [(0, 0, {'sequence': i, 'name': 'N%d' % i, 'latitude': -33.30 - i / 50.0,
                                 'longitude': -70.60, 'planned_offset_min': i * 12}) for i in range(1, 4)]})
        return route

    def test_a_bus_cannot_have_two_trips_at_the_same_time(self):
        self.trip()
        with self.assertRaises(ValidationError):
            self.trip(start_local=7.4)                  # 07:24, while the first one is still on

    def test_the_same_bus_can_do_other_routes_at_other_times(self):
        first = self.trip()
        second = self.trip(start_local=9.0, route=self.other_route())
        self.assertEqual(first.vehicle_id, second.vehicle_id)
        self.assertNotEqual(first.route_id, second.route_id)

    def test_back_to_back_trips_are_allowed(self):
        self.trip()                                     # 07:15 to 07:40
        self.assertTrue(self.trip(start_local=7.25 + 25 / 60.0))

    def test_another_bus_can_take_the_same_time(self):
        other = self.env['bus.vehicle'].create({'name': 'Bus 2'})
        self.trip()
        self.assertTrue(self.trip(bus=other))

    def test_a_cancelled_trip_frees_the_bus(self):
        first = self.trip()
        first.action_cancel()
        self.assertEqual(first.state, 'cancelled')
        self.assertTrue(self.trip())

    def test_trips_are_created_only_on_the_days_of_the_schedule(self):
        trips = self.schedule._generate_trips(MONDAY, MONDAY + timedelta(days=6))
        self.assertEqual(len(trips), 5)                 # Monday to Friday, not the weekend
        self.assertNotIn(SATURDAY, trips.mapped('date'))
        self.assertEqual(set(trips.mapped('vehicle_id')), {self.bus})

    def test_generating_twice_creates_nothing_new(self):
        self.schedule._generate_trips(MONDAY, MONDAY + timedelta(days=4))
        again = self.schedule._generate_trips(MONDAY, MONDAY + timedelta(days=4))
        self.assertFalse(again)
        self.assertEqual(self.env['bus.trip'].search_count([('schedule_id', '=', self.schedule.id)]), 5)

    def test_a_clash_skips_the_day_instead_of_stopping_the_cron(self):
        self.trip(start_local=7.3)                      # blocks Monday
        trips = self.schedule._generate_trips(MONDAY, MONDAY + timedelta(days=1))
        self.assertEqual(trips.mapped('date'), [MONDAY + timedelta(days=1)])

    def test_the_wizard_refuses_a_clash(self):
        self.trip(start_local=7.3)
        wizard = self.env['bus.trip.assign'].create({
            'schedule_id': self.schedule.id, 'vehicle_id': self.bus.id, 'date_from': MONDAY, 'date_to': MONDAY})
        with self.assertRaises(ValidationError):
            wizard.action_assign()

    def test_the_wizard_assigns_a_bus_for_the_period(self):
        other = self.env['bus.vehicle'].create({'name': 'Bus 2'})
        wizard = self.env['bus.trip.assign'].create({
            'schedule_id': self.schedule.id, 'vehicle_id': other.id,
            'date_from': MONDAY, 'date_to': MONDAY + timedelta(days=1)})
        action = wizard.action_assign()
        trips = self.env['bus.trip'].search(action['domain'])
        self.assertEqual(len(trips), 2)
        self.assertEqual(set(trips.mapped('vehicle_id')), {other})

    def test_the_wizard_period_is_checked(self):
        with self.assertRaises(ValidationError):
            self.env['bus.trip.assign'].create({
                'schedule_id': self.schedule.id, 'vehicle_id': self.bus.id,
                'date_from': MONDAY, 'date_to': MONDAY - timedelta(days=1)})

    def test_a_schedule_needs_a_valid_time_and_a_day(self):
        with self.assertRaises(ValidationError):
            self.schedule.departure_time = 24.0
        with self.assertRaises(ValidationError):
            self.schedule.write({'monday': False, 'tuesday': False, 'wednesday': False,
                                 'thursday': False, 'friday': False})

    def test_the_cron_creates_the_next_days_for_the_default_bus(self):
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.trip_horizon_days', '3')
        self.env['bus.route.schedule']._cron_generate_trips()
        self.assertTrue(self.env['bus.trip'].search_count([('schedule_id', '=', self.schedule.id)]))
