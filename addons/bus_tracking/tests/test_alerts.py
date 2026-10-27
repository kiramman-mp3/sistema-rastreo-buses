from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import STOPS, BusCase, traccar_position

KNOTS_90_KMH = 50.0   # 92.6 km/h, above the default 50 km/h limit
KNOTS_20_KMH = 11.0   # 20.4 km/h


@tagged('post_install', '-at_install')
class TestAlerts(BusCase):

    def setUp(self):
        super().setUp()
        self.now = fields.Datetime.now().replace(microsecond=0)
        self.Alert = self.env['bus.alert']

    def fix(self, minutes_ago):
        return (self.now - timedelta(minutes=minutes_ago)).strftime('%Y-%m-%dT%H:%M:%S.000+00:00')

    def report(self, minutes_ago, knots, lat=-33.40, lon=-70.50):
        return self.bus._apply_position(traccar_position(7, self.fix(minutes_ago), lat, lon, speed_knots=knots))

    def alerts(self, kind=None, state=None):
        domain = [('vehicle_id', '=', self.bus.id)]
        if kind:
            domain.append(('kind', '=', kind))
        if state:
            domain.append(('state', '=', state))
        return self.Alert.search(domain)

    # -- speeding --------------------------------------------------------
    def test_speeding_opens_tracks_the_peak_and_closes(self):
        self.report(10, KNOTS_20_KMH)
        self.assertFalse(self.alerts())
        self.report(9, KNOTS_90_KMH)
        alert = self.alerts('speeding')
        self.assertEqual(alert.state, 'open')
        self.assertAlmostEqual(alert.max_speed, 92.6, delta=0.1)
        self.assertEqual(alert.threshold, 50)
        self.report(8, 60.0)   # 111 km/h
        self.assertEqual(len(self.alerts('speeding')), 1)
        self.assertAlmostEqual(alert.max_speed, 111.1, delta=0.1)
        self.report(7, KNOTS_20_KMH)
        self.assertEqual(alert.state, 'closed')
        self.assertEqual(alert.end_time, self.now - timedelta(minutes=7))
        self.assertIn('limit 50', alert.detail)

    def test_new_speeding_episode_opens_a_new_alert(self):
        self.report(10, KNOTS_90_KMH)
        self.report(9, KNOTS_20_KMH)
        self.report(8, KNOTS_90_KMH)
        self.assertEqual(len(self.alerts('speeding')), 2)
        self.assertEqual(len(self.alerts('speeding', 'open')), 1)

    def test_speed_limit_zero_disables_speeding_alerts(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.speed_limit', '0')
        self.report(5, KNOTS_90_KMH)
        self.assertFalse(self.alerts())

    def test_speed_limit_is_configurable(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.speed_limit', '100')
        self.report(5, KNOTS_90_KMH)
        self.assertFalse(self.alerts())

    # -- no signal -------------------------------------------------------
    def test_silent_bus_raises_one_alert_and_new_report_closes_it(self):
        self.report(15, KNOTS_20_KMH)
        self.Alert._cron_check()
        self.Alert._cron_check()
        alert = self.alerts('offline')
        self.assertEqual(len(alert), 1)
        self.assertEqual(alert.start_time, self.now - timedelta(minutes=15))
        self.assertEqual(alert.threshold, 10)
        self.report(0, KNOTS_20_KMH)
        self.assertEqual(alert.state, 'closed')

    def test_bus_parked_overnight_is_not_reported_as_offline(self):
        self.report(8 * 60, KNOTS_20_KMH)
        self.Alert._cron_check()
        self.assertFalse(self.alerts('offline'))

    def test_recent_report_is_not_offline_and_zero_disables(self):
        self.report(3, KNOTS_20_KMH)
        self.Alert._cron_check()
        self.assertFalse(self.alerts('offline'))
        self.env['ir.config_parameter'].set_param('bus_tracking.offline_minutes', '0')
        self.bus.last_fix_time = self.now - timedelta(minutes=30)
        self.Alert._cron_check()
        self.assertFalse(self.alerts('offline'))

    # -- long stop -------------------------------------------------------
    def test_long_stop_away_from_any_stop(self):
        self.report(40, KNOTS_20_KMH)
        self.report(1, 0.0)
        self.Alert._cron_check()
        alert = self.alerts('long_stop')
        self.assertEqual(len(alert), 1)
        self.assertEqual(alert.start_time, self.now - timedelta(minutes=40))
        self.assertEqual(alert.threshold, 15)
        self.Alert._cron_check()
        self.assertEqual(len(self.alerts('long_stop')), 1)
        self.report(0, KNOTS_20_KMH)
        self.assertEqual(alert.state, 'closed')

    def test_short_stop_is_fine(self):
        self.report(10, KNOTS_20_KMH)
        self.report(1, 0.0)
        self.Alert._cron_check()
        self.assertFalse(self.alerts('long_stop'))

    def test_waiting_inside_a_stop_is_not_a_long_stop(self):
        name, lat, lon = STOPS[0]
        self.report(40, KNOTS_20_KMH)
        self.report(1, 0.0, lat=lat, lon=lon)
        self.assertEqual(self.bus.current_stop_id, self.stop['Terminal'])
        self.Alert._cron_check()
        self.assertFalse(self.alerts('long_stop'))

    def test_long_stop_needs_a_known_moment_of_movement(self):
        self.report(1, 0.0)
        self.Alert._cron_check()
        self.assertFalse(self.alerts('long_stop'))

    # -- data integrity --------------------------------------------------
    def test_database_allows_a_single_open_alert_per_bus_and_kind(self):
        vals = {'vehicle_id': self.bus.id, 'kind': 'offline', 'start_time': self.now}
        self.Alert.create(vals)
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.Alert.create(vals)
        closed = self.Alert.create(dict(vals, kind='speeding', state='closed'))
        self.Alert.create(dict(vals, kind='speeding', state='closed'))
        self.assertTrue(closed)

    def test_alert_keeps_the_route_it_had(self):
        self.report(5, KNOTS_90_KMH)
        alert = self.alerts('speeding')
        self.assertEqual(alert.route_id, self.route)
        other = self.env['bus.route'].create({'name': 'Otra', 'code': 'L2'})
        self.bus.route_id = other
        self.assertEqual(alert.route_id, self.route)

    def test_live_map_data_lists_open_alerts_with_labels(self):
        self.report(1, KNOTS_90_KMH)
        self.assertEqual(self.alerts('speeding', 'open').vehicle_id, self.bus)
        labels = dict(self.env['bus.alert']._fields['kind']._description_selection(self.env))
        self.assertEqual(labels['speeding'], 'Speeding')
