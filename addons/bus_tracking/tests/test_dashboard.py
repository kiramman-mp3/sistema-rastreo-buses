import json
from datetime import date
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, tagged

from .test_kpi import DAY, PAST, KpiCase


@tagged('post_install', '-at_install')
class TestDashboardData(KpiCase):
    """The series of the dashboard, against the hand-made trips of KpiCase (see there)."""

    def dash(self, **extra):
        return self.kpi.dashboard(**dict(self.period, **extra))

    def test_it_carries_the_indicators_and_the_previous_period(self):
        data = self.dash()
        self.assertEqual(len(data['metrics']), 12)
        self.assertEqual(set(data['previous']), {m['code'] for m in data['metrics']})
        self.assertEqual(data['scope'], 'all')
        self.assertTrue(data['can_manage'])
        self.assertEqual(data['kind_labels']['late_arrival'], 'Late arrival')
        self.assertIsNone(self.dash(compare=False)['previous'])

    def test_the_previous_period_is_the_one_just_before(self):
        """Trips A and B fall in the last two days; the two days before hold C (incomplete) and D (never started)."""
        data = self.dash(date_from=PAST - 1 * DAY, date_to=PAST)
        self.assertEqual(data['metrics'][0]['value'], 100.0)           # T1 of A and B: both done
        self.assertEqual(data['previous']['T1'], 0.0)                   # T1 of C and D: none done

    def test_each_line_has_its_figures(self):
        row, = [r for r in self.dash()['by_route'] if r['id'] == self.route.id]
        self.assertEqual((row['trips'], row['compliance'], row['punctuality'], row['delay']), (4, 50.0, 75.0, 11.5))
        trips = self.trip_a | self.trip_b | self.trip_c
        self.assertEqual(row['est_km'], round(sum(trips.mapped('distance_est_km')), 1))
        self.assertEqual(row['real_km'], round(sum(trips.mapped('distance_real_km')), 1))
        self.assertEqual(row['alerts'], 6)
        self.assertEqual(row['color'], '#3388ff')

    def test_a_line_without_trips_shows_empty_not_missing(self):
        other = self.env['bus.route'].create({'name': 'Otra', 'code': 'O1', 'color': '#1E5560'})
        row, = [r for r in self.dash()['by_route'] if r['id'] == other.id]
        self.assertEqual((row['trips'], row['compliance'], row['punctuality'], row['delay']), (0, None, None, None))

    def test_the_line_filter_keeps_only_that_line(self):
        other = self.env['bus.route'].create({'name': 'Otra', 'code': 'O1'})
        self.assertEqual([r['id'] for r in self.dash(route_ids=[other.id])['by_route']], [other.id])

    def test_each_day_has_its_trips_punctuality_and_alerts(self):
        days = {d['date']: d for d in self.dash()['by_day']}
        self.assertEqual((days[str(PAST)]['done'], days[str(PAST)]['punctuality']), (1, 100.0))
        self.assertEqual((days[str(PAST - DAY)]['done'], days[str(PAST - DAY)]['punctuality']), (1, 33.3))
        third = days[str(PAST - 2 * DAY)]
        self.assertEqual((third['incomplete'], third['punctuality']), (1, 100.0))
        self.assertIsNone(days[str(PAST - 3 * DAY)]['punctuality'])               # nobody drove it
        self.assertEqual(sum(d['alerts'] for d in days.values()), 6)

    def test_the_delays_fall_in_their_buckets(self):
        counts = [b['count'] for b in self.dash()['delay_buckets']]
        # on time or within 5 min: 6; 5 to 10 min: the 8; 10 to 15: the 15; nothing early, 15 to 20 or beyond
        self.assertEqual(counts, [0, 6, 1, 1, 0, 0])
        self.assertEqual(self.dash()['delay_buckets'][1]['label'], 'on time (within 5 min)')

    def test_the_stops_are_ranked_by_their_delay(self):
        stops = self.dash()['stop_delays']
        self.assertEqual([s['stop'] for s in stops], ['Hospital', 'Plaza', 'Terminal'])
        self.assertEqual([s['delay'] for s in stops], [5.0, 4.0, 0.0])
        self.assertEqual(stops[0]['arrivals'], 3)

    def test_the_incident_kinds_make_a_pareto(self):
        kinds = self.dash()['incident_kinds']
        self.assertEqual(sum(k['count'] for k in kinds), 6)
        self.assertEqual(kinds[-1]['cumulative'], 100.0)
        self.assertEqual([k['count'] for k in kinds], sorted((k['count'] for k in kinds), reverse=True))
        self.assertEqual(kinds[0]['count'], 2)

    def test_the_latest_trips_are_listed_with_what_the_rules_found(self):
        trips = {t['id']: t for t in self.dash()['trips']}
        late = trips[self.trip_b.id]
        self.assertEqual((late['state'], late['late'], late['visited'], late['delay_end']), ('done', 2, 3, 15.0))
        self.assertEqual(late['flags'], 'late')
        self.assertEqual(trips[self.trip_c.id]['flags'], 'incomplete,skipped')
        self.assertEqual(trips[self.trip_d.id]['flags'], 'incomplete,not_started')
        self.assertFalse(late['simulated'])

    def test_simulated_trips_can_be_left_out_or_shown_alone(self):
        simulated = self.env['bus.trip.simulator']._simulate(self.route, 'punctual', day=PAST - 4 * DAY)
        period = {'date_from': PAST - 6 * DAY, 'date_to': PAST}
        everything = {t['id'] for t in self.kpi.dashboard(scope='all', **period)['trips']}
        real = {t['id'] for t in self.kpi.dashboard(scope='real', **period)['trips']}
        only = {t['id'] for t in self.kpi.dashboard(scope='simulated', **period)['trips']}
        self.assertIn(simulated.id, everything)
        self.assertNotIn(simulated.id, real)
        self.assertEqual(only, {simulated.id})

    def test_response_time_days_come_from_the_samples(self):
        for ms in (100, 200, 300, 400, 500):
            self.env['bus.perf.sample'].create({'name': 'live', 'ms': ms})
        today = self.env['bus.perf.sample'].search([], limit=1).created.date()
        days = self.kpi.dashboard(date_from=PAST - 5 * DAY, date_to=today + DAY)['perf_days']
        self.assertEqual((days[0]['p50'], days[0]['p95'], days[0]['samples']), (300.0, 480.0, 5))


@tagged('post_install', '-at_install')
class TestDashboardRoute(HttpCase):

    def call(self, **params):
        resp = self.url_open('/bus_tracking/dashboard', data=json.dumps(
            {'jsonrpc': '2.0', 'method': 'call', 'params': params}), headers={'Content-Type': 'application/json'})
        return resp.json()

    def test_it_needs_a_session(self):
        self.assertIn('error', self.call(days=30))

    def test_a_user_outside_the_bus_groups_is_refused(self):
        self.env['res.users'].create({
            'name': 'Sin grupo', 'login': 'nogroup', 'password': 'nogroup-pass-1',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]})
        self.authenticate('nogroup', 'nogroup-pass-1')
        self.assertIn('error', self.call(days=30))

    def test_a_period_in_days_ends_today(self):
        self.authenticate('admin', 'admin')
        result = self.call(days=7)['result']
        self.assertEqual(len(result['metrics']), 12)
        self.assertEqual(result['period']['to'], str(self.env['bus.kpi']._period()[1]))

    def test_the_number_of_days_is_checked_and_limited(self):
        self.authenticate('admin', 'admin')
        self.assertIn('error', self.call(days='many'))
        long = self.call(days=100000)['result']['period']
        self.assertLessEqual((self.env['bus.kpi']._period()[1] - date.fromisoformat(long['from'])).days, 366)

    def test_dates_can_be_chosen(self):
        self.authenticate('admin', 'admin')
        result = self.call(date_from='2026-10-01', date_to='2026-10-10', scope='real')['result']
        self.assertEqual(result['period'], {'from': '2026-10-01', 'to': '2026-10-10'})
        self.assertEqual(result['scope'], 'real')


@tagged('post_install', '-at_install')
class TestDashboardActions(KpiCase):

    def viewer(self):
        return self.env['res.users'].create({
            'name': 'Lector', 'login': 'viewer-dash',
            'groups_id': [(6, 0, [self.env.ref('bus_tracking.group_bus_user').id])]})

    def test_only_managers_can_measure_and_audit_from_the_dashboard(self):
        viewer = self.viewer()
        with self.assertRaises(AccessError):
            self.env['bus.perf.sample'].with_user(viewer).action_measure()
        with self.assertRaises(AccessError):
            self.env['bus.sync.audit'].with_user(viewer).action_run()
        self.assertEqual(self.env['bus.perf.sample'].action_measure(), 4)

    def test_the_audit_from_the_dashboard_says_when_traccar_is_not_set_up(self):
        with patch('odoo.addons.bus_tracking.models.traccar_api.BusTraccarApi.is_configured', return_value=False):
            with self.assertRaises(UserError):
                self.env['bus.sync.audit'].action_run()

    def test_a_viewer_does_not_get_the_manager_buttons(self):
        viewer = self.viewer()
        self.assertFalse(self.kpi.with_user(viewer).dashboard()['can_manage'])
