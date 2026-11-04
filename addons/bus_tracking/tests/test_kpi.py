from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from ..models.bus_kpi import SQL
from .test_trip_run import HOSPITAL, PAST, PLAZA, TERMINAL, RunCase

DAY = timedelta(days=1)


def by_code(result):
    return {m['code']: m for m in result['metrics']}


class KpiCase(RunCase):
    """Four closed trips of the test route, built by hand so every indicator has a result known in advance.

    - trip A, punctual: Terminal 0, Plaza +10, Hospital +25                      -> done, 3 on time
    - trip B, late:     Terminal 0, Plaza +18 (8 late), Hospital +40 (15 late)   -> done, 2 late
    - trip C, skipped:  Terminal 0, Hospital +25, never at the Plaza             -> incomplete
    - trip D, no show:  nobody drove it                                          -> incomplete, 3 stops skipped
    """

    def setUp(self):
        super().setUp()
        self.trip_a = self.trip_                                           # PAST
        self.trip_b = self.trip(day=PAST - DAY)
        self.trip_c = self.trip(day=PAST - 2 * DAY)
        self.trip_d = self.trip(day=PAST - 3 * DAY)
        # the bus drives them in the order of the calendar: a position older than the last one is ignored
        self.at(0, TERMINAL, trip=self.trip_c)
        self.at(25, HOSPITAL, trip=self.trip_c)
        self.at(0, TERMINAL, trip=self.trip_b)
        self.at(18, PLAZA, trip=self.trip_b)
        self.at(40, HOSPITAL, trip=self.trip_b)
        self.at(0, TERMINAL, trip=self.trip_a)
        self.at(10, PLAZA, trip=self.trip_a)
        self.at(25, HOSPITAL, trip=self.trip_a)
        self.env['bus.trip']._cron_close_trips()
        self.kpi = self.env['bus.kpi']
        self.period = {'date_from': PAST - 5 * DAY, 'date_to': PAST}

    def metrics(self, **extra):
        return by_code(self.kpi.compute(**dict(self.period, **extra)))


@tagged('post_install', '-at_install')
class TestTransportIndicators(KpiCase):

    def test_the_trips_are_what_the_test_expects(self):
        self.assertEqual([t.state for t in (self.trip_a, self.trip_b, self.trip_c, self.trip_d)],
                         ['done', 'done', 'incomplete', 'incomplete'])

    def test_route_compliance(self):
        metric = self.metrics()['T1']
        self.assertEqual(metric['value'], 50.0)                    # 2 done of 4 closed
        self.assertIn('2 of 4', metric['detail'])

    def test_punctuality_counts_early_as_punctual(self):
        # arrivals: A 3, B 3, C 2 = 8; late: 2 -> 6 of 8
        self.assertEqual(self.metrics()['T2']['value'], 75.0)

    def test_average_delay(self):
        metric = self.metrics()['T3']
        self.assertEqual(metric['value'], 11.5)                    # (8 + 15) / 2
        self.assertIn('2 late arrivals', metric['detail'])
        self.assertIn('15', metric['detail'])

    def test_stops_served(self):
        self.assertEqual(self.metrics()['T4']['value'], 66.7)      # 8 of the 12 planned stops

    def test_estimated_against_driven_distance_follows_its_formula(self):
        trips = (self.trip_a | self.trip_b | self.trip_c)
        estimated, driven = sum(trips.mapped('distance_est_km')), sum(trips.mapped('distance_real_km'))
        self.assertGreater(driven, 0)
        self.assertEqual(self.metrics()['T6']['value'], round((driven - estimated) / estimated * 100.0, 1))

    def test_average_trip_time_is_judged_against_the_plan(self):
        metric = self.metrics()['T7']
        self.assertEqual(metric['value'], 32.5)                    # trips of 25 and 40 minutes
        self.assertIn('planned 25.0 min', metric['detail'])
        self.assertIn('30.0 %', metric['detail'])
        self.assertEqual(metric['status'], 'warn')                 # 30 % off the plan: acceptable, not good

    def test_deviation_uses_the_positions_of_the_trips(self):
        metric = self.metrics()['T5']
        self.assertIsNotNone(metric['value'])
        self.assertLess(metric['value'], 50)                       # they drive along the line
        self.assertEqual(metric['status'], 'good')

    def test_incidents_count_alerts_and_incidents(self):
        # late arrivals 2, skipped stop 1, incomplete trips 2, late start 1
        metric = self.metrics()['T8']
        self.assertEqual(metric['value'], 6)
        self.assertIn('6 alerts and 0 incidents', metric['detail'])
        user = self.env['res.users'].create({'name': 'Chofer', 'login': 'kpi-chofer'})
        shift = self.env['bus.shift'].create({
            'user_id': user.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id,
            'start': self.trip_a.planned_start})
        self.env['bus.incident'].create({
            'shift_id': shift.id, 'vehicle_id': self.bus.id, 'kind': 'traffic',
            'reported_at': self.trip_a.planned_start + timedelta(minutes=5)})
        self.assertEqual(self.metrics()['T8']['value'], 7)

    def test_the_indicators_move_when_the_data_moves(self):
        """Nothing is static: one more trip that nobody drove changes the figures."""
        self.assertEqual(self.metrics()['T1']['value'], 50.0)
        extra = self.trip(day=PAST - 4 * DAY)
        self.env['bus.trip']._cron_close_trips()
        self.assertEqual(extra.state, 'incomplete')
        self.assertEqual(self.metrics()['T1']['value'], 40.0)                 # 2 done of 5 closed
        self.assertEqual(self.metrics()['T8']['value'], 8)                    # plus its late start and incomplete trip


@tagged('post_install', '-at_install')
class TestFilters(KpiCase):

    def test_the_period_limits_the_trips(self):
        empty = self.metrics(date_from=PAST + DAY, date_to=PAST + 5 * DAY)
        self.assertIsNone(empty['T1']['value'])
        self.assertEqual(self.metrics(date_from=PAST, date_to=PAST)['T1']['value'], 100.0)      # trip A alone

    def test_the_period_defaults_to_the_last_thirty_days(self):
        result = self.kpi.compute()
        start, end = result['period']['from'], result['period']['to']
        self.assertEqual((fields.Date.to_date(end) - fields.Date.to_date(start)).days, 29)

    def test_a_reversed_period_is_put_in_order(self):
        self.assertEqual(self.kpi._period(PAST, PAST - 3 * DAY), (PAST - 3 * DAY, PAST))

    def test_routes_can_be_chosen(self):
        other = self.env['bus.route'].create({'name': 'Otra', 'code': 'O1'})
        self.assertIsNone(self.metrics(route_ids=[other.id])['T1']['value'])
        self.assertEqual(self.metrics(route_ids=[self.route.id])['T1']['value'], 50.0)

    def test_real_and_simulated_data_are_told_apart(self):
        simulated = self.env['bus.trip.simulator']._simulate(self.route, 'late', day=PAST - 4 * DAY)
        self.assertTrue(simulated.simulated)
        period = {'date_from': PAST - 6 * DAY, 'date_to': PAST}
        everything = by_code(self.kpi.compute(scope='all', **period))['T1']['value']
        real = by_code(self.kpi.compute(scope='real', **period))['T1']['value']
        only_simulated = by_code(self.kpi.compute(scope='simulated', **period))['T1']['value']
        self.assertEqual(real, 50.0)
        self.assertEqual(only_simulated, 100.0)
        self.assertEqual(everything, 60.0)                          # 3 done of 5


@tagged('post_install', '-at_install')
class TestSoftwareIndicators(KpiCase):

    def test_gps_integrity_counts_what_was_refused(self):
        today = {'date_from': PAST - 5 * DAY, 'date_to': fields.Date.today() + DAY}
        stored = self.env['bus.position'].search_count([('vehicle_id', '=', self.bus.id)])
        self.assertEqual(by_code(self.kpi.compute(**today))['S1']['value'], 100.0)
        self.env['bus.position.reject']._log({'deviceId': 7}, 'latitude out of range')
        self.env['bus.position.reject']._log({'deviceId': 7}, 'bad time')
        metric = by_code(self.kpi.compute(**today))['S1']
        self.assertEqual(metric['value'], round(100.0 * stored / (stored + 2), 1))
        self.assertIn('2 rejected', metric['detail'])

    def test_sync_accuracy_comes_from_the_audits(self):
        today = {'date_from': PAST - 5 * DAY, 'date_to': fields.Date.today() + DAY}
        self.assertIsNone(by_code(self.kpi.compute(**today))['S2']['value'])
        self.env['bus.sync.audit'].create({'vehicle_id': self.bus.id, 'total': 100, 'matched': 99})
        metric = by_code(self.kpi.compute(**today))['S2']
        self.assertEqual((metric['value'], metric['status']), (99.0, 'good'))

    def test_response_time_is_a_percentile_of_the_samples(self):
        today = {'date_from': PAST - 5 * DAY, 'date_to': fields.Date.today() + DAY}
        self.assertIsNone(by_code(self.kpi.compute(**today))['S3']['value'])
        for ms in (100, 200, 300, 400, 500):
            self.env['bus.perf.sample'].create({'name': 'live', 'ms': ms})
        metric = by_code(self.kpi.compute(**today))['S3']
        self.assertEqual(metric['value'], 480.0)                    # p95 of 100..500
        self.assertIn('median 300.0 ms', metric['detail'])
        self.assertEqual(metric['status'], 'good')

    def test_detection_is_measured_on_the_simulated_trips(self):
        sim = self.env['bus.trip.simulator']
        trips = self.env['bus.trip']
        for i, scenario in enumerate(('punctual', 'late', 'skipped_stop', 'early')):
            trips |= sim._simulate(self.route, scenario, day=PAST - (10 + i) * DAY)
        period = {'date_from': PAST - 20 * DAY, 'date_to': PAST}
        metric = by_code(self.kpi.compute(scope='simulated', **period))['S4']
        self.assertEqual(metric['value'], 100.0)
        self.assertIn('precision 100.0 %', metric['detail'])
        # a wrong expectation lowers it: the 'early' trip was meant to be punctual
        trips.filtered(lambda t: t.scenario == 'early').expected_flags = ''
        metric = by_code(self.kpi.compute(scope='simulated', **period))['S4']
        self.assertEqual(metric['value'], 75.0)
        self.assertIn('precision', metric['detail'])

    def test_no_simulated_trips_means_no_value(self):
        self.assertIsNone(self.metrics(scope='real')['S4']['value'])


@tagged('post_install', '-at_install')
class TestDefinitions(KpiCase):

    def test_every_indicator_has_formula_source_unit_and_interpretation(self):
        metrics = self.kpi.compute()['metrics']
        self.assertEqual([m['code'] for m in metrics],
                         ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'S1', 'S2', 'S3', 'S4'])
        for metric in metrics:
            for key in ('name', 'formula', 'source', 'unit', 'interpretation'):
                self.assertTrue(metric[key], (metric['code'], key))
            self.assertIn(metric['group'], ('transport', 'software'))
        self.assertEqual(len([m for m in metrics if m['group'] == 'transport']), 8)
        self.assertEqual(len([m for m in metrics if m['group'] == 'software']), 4)

    def test_every_calculated_indicator_shows_the_query_that_reproduces_it(self):
        for metric in self.kpi.compute()['metrics']:
            self.assertIn('SELECT', metric['sql'].upper(), metric['code'])

    def test_the_status_follows_the_thresholds(self):
        for value, status in ((95, 'good'), (80, 'warn'), (50, 'bad')):
            self.assertEqual(self.kpi._status('T1', value), status)
        for value, status in ((4, 'good'), (8, 'warn'), (12, 'bad')):          # lower is better
            self.assertEqual(self.kpi._status('T3', value), status)
        self.assertEqual(self.kpi._status('T1', None), 'na')
        self.assertEqual(self.kpi._status('T8', 3), 'na')                        # incidents have no threshold

    def test_the_sql_can_be_run_as_shown(self):
        """The queries are the evidence: running T1 by hand gives the same figure."""
        self.env.flush_all()
        params = self.kpi._params(PAST - 5 * DAY, PAST)
        self.env.cr.execute(SQL['T1'], params)
        done, total = self.env.cr.fetchone()
        self.assertEqual((done, total), (2, 4))
