import json
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged

from ..models.bus_trip import local_to_utc
from .common import traccar_position
from .test_driver_auth import make_driver


def simulate(env, route, scenario, driver=None, days_ago=1):
    return env['bus.trip.simulator']._simulate(route, scenario, days_ago=days_ago, driver=driver)


@tagged('post_install', '-at_install')
class TestFineDetection(TransactionCase):
    """Each rule of a fine, from the trip simulator through the real rules of the system to a proposed fine."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # stretches of about 5.5 km: long enough for a deviation and a speeding run of several minutes
        cls.route = cls.env['bus.route'].create({
            'name': 'Linea Multas', 'code': 'LM',
            'stop_ids': [(0, 0, {'sequence': i, 'name': 'Parada %d' % i, 'latitude': -1.2 - i * 0.05,
                                 'longitude': -78.6, 'radius': 60}) for i in range(4)]})
        cls.driver = make_driver(cls.env, login='chofer_detector')

    def fines_of(self, trip):
        return self.env['bus.fine'].search([('trip_id', '=', trip.id)])

    def check(self, fine, key):
        return next(c for c in fine._checks() if c['key'] == key)

    def test_speeding_beyond_the_tolerance_is_proposed(self):
        trip = simulate(self.env, self.route, 'speeding', self.driver)
        fine = self.fines_of(trip)
        self.assertEqual(len(fine), 1)
        self.assertEqual((fine.rule, fine.state, fine.driver_id), ('speeding', 'new', self.driver))
        self.assertAlmostEqual(fine.measured_value, 82.0, places=0)
        self.assertGreaterEqual(fine.measured_seconds, 30)
        self.assertTrue(fine.checks_ok)
        self.assertTrue(fine.simulated)
        self.assertEqual(fine.amount_proposed, 25.0)
        self.assertIn('82', fine.summary)
        evidence = fine._evidence()
        self.assertEqual(evidence['chart'], {'limit': 50, 'threshold': 70.0})
        self.assertTrue(any(point[4] for point in evidence['track']))      # the stretch over 70 km/h is marked
        self.assertTrue(evidence['route'])
        self.assertEqual(self.check(fine, 'driver')['params']['how'], 'trip')

    def test_speeding_inside_the_tolerance_is_only_an_alert(self):
        trip = simulate(self.env, self.route, 'speeding_tolerated', self.driver)
        self.assertTrue(trip.alert_ids.filtered(lambda a: a.kind == 'speeding'))
        self.assertFalse(self.fines_of(trip))
        self.assertTrue(all(trip.alert_ids.mapped('fine_checked')))

    def test_deviation(self):
        trip = simulate(self.env, self.route, 'deviation', self.driver)
        fine = self.fines_of(trip).filtered(lambda f: f.rule == 'off_route')
        self.assertEqual(len(fine), 1)
        self.assertGreater(fine.measured_value, 300)
        self.assertGreaterEqual(fine.measured_seconds, 180)
        self.assertEqual(fine._evidence()['corridor_m'], 150)
        self.assertTrue(fine.checks_ok)

    def test_long_stop_is_seen_when_the_bus_moves_again(self):
        trip = simulate(self.env, self.route, 'long_stop', self.driver)
        alert = self.env['bus.alert'].search([('vehicle_id', '=', trip.vehicle_id.id), ('kind', '=', 'long_stop')])
        self.assertEqual(len(alert), 1)
        self.assertEqual(alert.state, 'closed')
        fine = self.fines_of(trip).filtered(lambda f: f.rule == 'long_stop')
        self.assertEqual(len(fine), 1)
        self.assertGreaterEqual(fine.measured_value, 25)
        self.assertTrue(fine.checks_ok, fine._checks())

    def test_skipped_stop(self):
        trip = simulate(self.env, self.route, 'skipped_stop', self.driver)
        fines = self.fines_of(trip)
        skipped = fines.filtered(lambda f: f.rule == 'skipped_stop')
        self.assertEqual(len(skipped), 1)
        self.assertGreater(skipped.measured_value, 60)
        # the stops in the middle are skipped stops, not an incomplete trip: no fine twice for the same stop
        self.assertFalse(fines.filtered(lambda f: f.rule == 'incomplete_trip'))

    def test_incomplete_trip_is_one_fine(self):
        trip = simulate(self.env, self.route, 'incomplete_end', self.driver)
        fines = self.fines_of(trip)
        self.assertEqual(fines.mapped('rule'), ['incomplete_trip'])
        self.assertEqual(fines.measured_value, 1)
        self.assertTrue(fines.checks_ok, fines._checks())

    def test_a_trip_without_positions_cannot_be_proved(self):
        trip = simulate(self.env, self.route, 'not_started', self.driver)
        fines = self.fines_of(trip)
        self.assertEqual(fines.mapped('rule'), ['late_start'])
        self.assertEqual((fines.state, fines.discard_reason), ('discarded', 'system'))
        self.assertFalse(self.check(fines, 'gps')['ok'])

    def test_punctual_trip_has_no_fine(self):
        trip = simulate(self.env, self.route, 'punctual', self.driver)
        self.assertFalse(self.fines_of(trip))

    def test_without_a_driver_the_system_discards_it(self):
        trip = simulate(self.env, self.route, 'speeding')
        fine = self.fines_of(trip)
        self.assertEqual((fine.state, fine.discard_reason), ('discarded', 'system'))
        self.assertFalse(fine.driver_id)
        self.assertFalse(self.check(fine, 'driver')['ok'])

    def test_an_incident_explains_it(self):
        bus = self.env['bus.trip.simulator']._vehicle_for(self.route)
        day = self.env['bus.trip.simulator']._day_for(1, self.route)
        start = local_to_utc(day, 6.5)
        shift = self.env['bus.shift'].create({'user_id': self.driver.id, 'vehicle_id': bus.id,
                                              'route_id': self.route.id, 'start': start, 'state': 'done',
                                              'end': start + timedelta(hours=3)})
        self.env['bus.incident'].create({'shift_id': shift.id, 'vehicle_id': bus.id, 'kind': 'breakdown',
                                         'reported_at': start + timedelta(minutes=35)})
        trip = self.env['bus.trip.simulator']._simulate(self.route, 'speeding', day=day, driver=self.driver)
        fine = self.fines_of(trip)
        self.assertEqual(fine.state, 'discarded')
        incident = self.check(fine, 'incident')
        self.assertFalse(incident['ok'])
        self.assertEqual(incident['params']['kinds'], ['breakdown'])

    def test_repeat_offence_costs_more(self):
        first = self.fines_of(simulate(self.env, self.route, 'speeding', self.driver, days_ago=3))
        first.action_fine()
        second = self.fines_of(simulate(self.env, self.route, 'speeding', self.driver, days_ago=1))
        self.assertTrue(second.recurrent)
        self.assertEqual(second.amount_proposed, 37.5)

    def test_the_fines_set_of_the_wizard_shows_every_rule(self):
        wizard = self.env['bus.trip.simulate'].create({'route_id': self.route.id, 'scenario': 'punctual',
                                                       'driver_user_id': self.driver.id})
        fines = self.env['bus.fine'].search(wizard.action_fines_set()['domain'])
        proposed = fines.filtered(lambda f: f.state == 'new')
        self.assertEqual(set(proposed.mapped('rule')),
                         {'speeding', 'off_route', 'long_stop', 'skipped_stop', 'incomplete_trip'})
        self.assertEqual(fines.filtered(lambda f: f.state == 'discarded').mapped('rule'), ['late_start'])
        self.assertEqual(set(fines.mapped('driver_id')), {self.driver})

    def test_the_reasons_are_written_out(self):
        fine = self.fines_of(simulate(self.env, self.route, 'speeding', self.driver))
        self.assertIn('70 km/h', fine.summary)
        self.assertEqual(len(fine._checks_rendered()), 4)
        self.assertIn('o_bus_fine_ok', fine.check_lines)
        self.assertNotIn('o_bus_fine_ko', fine.check_lines)


@tagged('post_install', '-at_install')
class TestFineCron(TransactionCase):
    """The real flow: positions from the GPS of a bus on a shift, the alert closes, the cron proposes the fine."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.route = cls.env['bus.route'].create({
            'name': 'Linea Cron', 'code': 'LC',
            'stop_ids': [(0, 0, {'sequence': i, 'name': 'Cron %d' % i, 'latitude': -1.3 - i * 0.05,
                                 'longitude': -78.7, 'radius': 60}) for i in range(3)]})
        cls.bus = cls.env['bus.vehicle'].create({'name': 'Bus Cron', 'route_id': cls.route.id,
                                                 'traccar_device_id': 991, 'traccar_unique_id': 'CRON991'})
        cls.driver = make_driver(cls.env, login='chofer_cron')
        cls.shift = cls.env['bus.shift'].create({'user_id': cls.driver.id, 'vehicle_id': cls.bus.id,
                                                 'route_id': cls.route.id,
                                                 'start': fields.Datetime.now() - timedelta(hours=1)})

    def drive(self, speeds, start, every=10):
        for i, kmh in enumerate(speeds):
            when = start + timedelta(seconds=i * every)
            self.bus._apply_position(traccar_position(
                991, when.strftime('%Y-%m-%dT%H:%M:%SZ'), -1.3 - 0.0005 * i, -78.7, speed_knots=kmh / 1.852))

    def test_cron_proposes_the_fine_of_a_closed_alert(self):
        start = fields.Datetime.now() - timedelta(minutes=10)
        self.drive([40, 80, 85, 90, 84, 78, 30], start)
        alert = self.env['bus.alert'].search([('vehicle_id', '=', self.bus.id), ('kind', '=', 'speeding')])
        self.assertEqual(alert.state, 'closed')
        fines = self.env['bus.fine']._cron_detect()
        self.assertEqual(len(fines), 1)
        self.assertEqual(fines.driver_id, self.driver)
        self.assertEqual(fines.shift_id, self.shift)
        self.assertEqual(fines.measured_seconds, 40)
        self.assertEqual(round(fines.measured_value), 90)
        self.assertTrue(alert.fine_checked)
        self.assertFalse(self.env['bus.fine']._cron_detect())       # once per alert

    def test_a_single_reading_above_the_tolerance_is_not_a_fine(self):
        start = fields.Datetime.now() - timedelta(minutes=10)
        self.drive([40, 95, 40], start)
        self.assertFalse(self.env['bus.fine']._cron_detect())

    def test_an_open_alert_waits(self):
        start = fields.Datetime.now() - timedelta(minutes=10)
        self.drive([80, 85, 90, 88], start)
        self.assertFalse(self.env['bus.fine']._cron_detect())
        self.assertFalse(self.env['bus.alert'].search([('kind', '=', 'speeding'),
                                                       ('vehicle_id', '=', self.bus.id)]).fine_checked)

    def test_alerts_that_never_become_fines_are_marked_checked(self):
        alert = self.env['bus.alert'].create({'vehicle_id': self.bus.id, 'kind': 'offline', 'state': 'closed',
                                              'start_time': fields.Datetime.now(), 'end_time': fields.Datetime.now()})
        self.env['bus.fine']._cron_detect()
        self.assertTrue(alert.fine_checked)

    def test_a_disabled_type_proposes_nothing(self):
        self.env.ref('bus_tracking.fine_type_speeding').active = False
        start = fields.Datetime.now() - timedelta(minutes=10)
        self.drive([40, 80, 85, 90, 84, 78, 30], start)
        self.assertFalse(self.env['bus.fine']._cron_detect())

    def test_the_evidence_is_kept_when_the_positions_are_gone(self):
        start = fields.Datetime.now() - timedelta(minutes=10)
        self.drive([40, 80, 85, 90, 84, 78, 30], start)
        fine = self.env['bus.fine']._cron_detect()
        self.env['bus.position'].search([('vehicle_id', '=', self.bus.id)]).unlink()
        track = json.loads(fine.evidence_json)['track']
        self.assertEqual(len(track), 7)
        self.assertEqual(sum(point[4] for point in track), 5)
