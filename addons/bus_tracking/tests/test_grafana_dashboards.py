"""The Grafana dashboards (bi/grafana/dashboards/*.json), against a database with known trips.

The dashboards are files outside the module: the tests look for them in the folder `bi` of the repository (or in
/mnt/bi, or in BUS_BI_DIR) and are skipped when it is not there.
"""
import json
import os
import re
from datetime import datetime, time
from pathlib import Path

from odoo.tests import tagged

from ..models.bus_alert import KINDS as ALERT_KINDS
from ..models.bus_grafana import DASHBOARDS
from ..models.bus_incident import KINDS as INCIDENT_KINDS
from .test_grafana_views import ViewCase
from .test_kpi import DAY, PAST, by_code


def bi_dir():
    for candidate in (os.environ.get('BUS_BI_DIR'), '/mnt/bi', Path(__file__).resolve().parents[3] / 'bi'):
        if candidate and (Path(candidate) / 'grafana' / 'dashboards').is_dir():
            return Path(candidate) / 'grafana'
    return None


def load_dashboards():
    folder = bi_dir()
    return {p.stem: json.loads(p.read_text(encoding='utf8')) for p in sorted((folder / 'dashboards').glob('*.json'))}


def panels(board):
    return [p for p in board['panels'] if p['type'] != 'row']


def queries(board):
    for panel in panels(board):
        for target in panel.get('targets', []):
            yield panel, target['rawSql']


class DashboardCase(ViewCase):
    """What Grafana does before it sends a query: it fills in the time range and the variables."""

    def setUp(self):
        super().setUp()
        if not bi_dir():
            self.skipTest('the folder bi/ is not available')
        self.boards = load_dashboards()
        self.t_from = datetime.combine(PAST - 5 * DAY, time(5, 0))        # midnight in Ecuador, in UTC
        self.t_to = datetime.combine(PAST + DAY, time(5, 0))

    def values(self, board, scope='all', trip=None):
        found = {'scope': scope}
        for variable in board['templating']['list']:
            if variable['type'] == 'query' and variable['name'] != 'trip':
                found[variable['name']] = ','.join("'%s'" % r[0] for r in self.rows(
                    self.expand(variable['query'], {})))
        found['trip'] = str(trip or self.trip_a.id)
        return found

    def expand(self, sql, found):
        sql = re.sub(r'\$__timeFilter\((\w+)\)', lambda m: "%s BETWEEN '%s' AND '%s'" % (
            m.group(1), self.t_from, self.t_to), sql)
        sql = sql.replace('$__timeFrom()', "'%s'" % self.t_from).replace('$__timeTo()', "'%s'" % self.t_to)
        for name, value in found.items():
            sql = sql.replace('${%s}' % name, value).replace('$' + name, value)
        self.assertNotIn('$', sql.replace('$$', ''))
        return sql

    def query(self, board, sql, **extra):
        return self.rows(self.expand(sql, self.values(board, **extra)))


@tagged('post_install', '-at_install')
class TestDashboardFiles(DashboardCase):

    def test_the_six_dashboards_are_there_with_the_uids_odoo_knows(self):
        uids = [b['uid'] for b in self.boards.values()]
        self.assertEqual(uids, [uid for uid, _title in DASHBOARDS])

    def test_they_refresh_every_thirty_seconds_and_cannot_be_edited(self):
        for name, board in self.boards.items():
            self.assertEqual(board['refresh'], '30s', name)
            self.assertFalse(board['editable'], name)
            self.assertEqual(board['timezone'], 'America/Guayaquil', name)
            self.assertEqual(board['time']['from'], 'now-30d', name)

    def test_they_have_the_filters_of_line_bus_and_data(self):
        for name, board in self.boards.items():
            variables = {v['name']: v for v in board['templating']['list']}
            self.assertTrue({'route', 'bus', 'scope'} <= set(variables), name)
            self.assertTrue(variables['route']['includeAll'] and variables['route']['multi'], name)
            self.assertEqual(variables['scope']['current']['value'], 'all', name)

    def test_every_panel_reads_the_database_of_odoo_with_a_query(self):
        for name, board in self.boards.items():
            for panel in panels(board):
                self.assertEqual(panel['datasource']['uid'], 'bus-kpi', '%s: %s' % (name, panel['title']))
                self.assertTrue(panel['targets'], '%s: %s' % (name, panel['title']))

    def test_the_ids_of_the_panels_are_not_repeated(self):
        for name, board in self.boards.items():
            ids = [p['id'] for p in board['panels']]
            self.assertEqual(len(ids), len(set(ids)), name)

    def test_the_twelve_indicators_are_on_the_summary(self):
        titles = [p['title'] for p in panels(self.boards['01-resumen']) if p['type'] == 'stat']
        self.assertEqual([t[:2] for t in titles], ['T%d' % n for n in range(1, 9)] + ['S%d' % n for n in range(1, 5)])

    def test_the_thresholds_are_the_ones_of_the_indicators(self):
        stats = {p['title'][:2]: p for p in panels(self.boards['01-resumen']) if p['type'] == 'stat'}
        steps = {code: [s['value'] for s in p['fieldConfig']['defaults']['thresholds']['steps']]
                 for code, p in stats.items()}
        self.assertEqual(steps['T1'], [None, 75, 90])
        self.assertEqual(steps['S1'], [None, 95, 99])
        self.assertEqual(steps['S3'][0], None)
        self.assertAlmostEqual(steps['S3'][1], 500, places=3)
        self.assertAlmostEqual(steps['S3'][2], 2000, places=3)

    def test_every_kind_of_alert_and_incident_has_its_name(self):
        text = json.dumps(self.boards['05-incidencias'], ensure_ascii=False)
        for kind, _label in ALERT_KINDS + INCIDENT_KINDS:
            self.assertIn("WHEN '%s' THEN" % kind, text)

    def test_the_datasource_and_the_provider_are_provisioned(self):
        folder = bi_dir() / 'provisioning'
        source = (folder / 'datasources' / 'odoo.yml').read_text(encoding='utf8')
        self.assertIn('uid: bus-kpi', source)
        self.assertIn('user: grafana_reader', source)
        self.assertNotIn('password: grafana', source)                  # the password comes from the environment
        provider = (folder / 'dashboards' / 'odoo.yml').read_text(encoding='utf8')
        self.assertIn('allowUiUpdates: false', provider)


@tagged('post_install', '-at_install')
class TestDashboardQueries(DashboardCase):
    """Every query of every panel runs, on data that exists, and only reads the kpi_* views."""

    def test_every_query_runs(self):
        count = 0
        for name, board in self.boards.items():
            for panel, sql in queries(board):
                rows = self.query(board, sql)
                self.assertIsInstance(rows, list, '%s: %s' % (name, panel['title']))
                count += 1
        self.assertGreater(count, 40)

    def test_they_read_only_the_views_of_the_module(self):
        allowed = {'kpi_routes', 'kpi_route_stops', 'kpi_trips', 'kpi_trip_stops', 'kpi_alerts', 'kpi_positions',
                   'kpi_positions_daily', 'kpi_response', 'kpi_software'}
        for name, board in self.boards.items():
            sqls = [sql for _panel, sql in queries(board)] + [v['query'] for v in board['templating']['list']
                                                              if v['type'] == 'query']
            for sql in sqls:
                own = set(re.findall(r'(?:WITH|,)\s+(\w+)\s+AS\s*\(', sql))          # names the query gives itself
                used = set(re.findall(r'(?:FROM|JOIN)\s+(\w+)', sql)) - own
                self.assertTrue(used <= allowed, '%s: %s' % (name, used - allowed))

    def test_the_line_filter_narrows_the_results(self):
        board = self.boards['02-rutas']
        panel = next(p for p in panels(board) if p['title'] == 'Puntualidad por línea (%)')
        sql = panel['targets'][0]['rawSql']
        everything = self.rows(self.expand(sql, self.values(board)))
        found = self.values(board)
        found['route'] = "'%s'" % self.route.code
        one = self.rows(self.expand(sql, found))
        self.assertEqual([r[0] for r in one], [self.route.code])
        self.assertGreaterEqual(len(everything), len(one))

    def test_the_data_filter_separates_real_from_simulated_trips(self):
        sim = self.env['bus.trip.simulator']._simulate(self.route, 'punctual', day=PAST - 4 * DAY)
        board = self.boards['04-recorridos']
        sql = next(p for p in panels(board) if p['title'] == 'Recorridos del periodo')['targets'][0]['rawSql']
        shown = {scope: {r[0] for r in self.query(board, sql, scope=scope)} for scope in ('all', 'real', 'simulated')}
        self.assertIn(sim.id, shown['all'])
        self.assertNotIn(sim.id, shown['real'])
        self.assertEqual(shown['simulated'], {sim.id})
        self.assertTrue({self.trip_a.id, self.trip_b.id} <= shown['real'])

    def test_the_stops_of_a_trip_come_in_order_with_local_times(self):
        board = self.boards['04-recorridos']
        sql = next(p for p in panels(board) if p['title'] == 'Paradas del recorrido elegido')['targets'][0]['rawSql']
        rows = self.query(board, sql, trip=self.trip_b.id)
        self.assertEqual([r[1] for r in rows], ['Terminal', 'Plaza', 'Hospital'])
        self.assertEqual(rows[0][2], '07:15')                           # planned 07:15 in Ecuador, 12:15 UTC
        self.assertEqual(rows[1][5], 8.0)

    def test_the_map_gets_the_positions_and_the_stops_of_the_trip(self):
        board = self.boards['04-recorridos']
        geo = next(p for p in panels(board) if p['type'] == 'geomap')
        positions, stops = (self.query(board, t['rawSql']) for t in geo['targets'])
        self.assertEqual(len(positions), 3)
        self.assertEqual([r[0] for r in stops], ['Terminal', 'Plaza', 'Hospital'])
        self.assertEqual(geo['options']['basemap']['type'], 'osm-standard')

    def test_the_pareto_adds_up_to_one_hundred(self):
        board = self.boards['05-incidencias']
        sql = next(p for p in panels(board) if p['title'].startswith('Pareto'))['targets'][0]['rawSql']
        rows = self.query(board, sql)
        self.assertTrue(rows)
        self.assertEqual(float(rows[-1][2]), 100.0)
        self.assertEqual([r[1] for r in rows], sorted((r[1] for r in rows), reverse=True))

    def test_the_comparison_table_has_this_period_and_the_one_before(self):
        board = self.boards['01-resumen']
        sql = next(p for p in panels(board) if p['title'] == 'Este periodo contra el anterior')['targets'][0]['rawSql']
        rows = {r[0][:2]: r for r in self.query(board, sql)}
        self.assertEqual(set(rows), {'T1', 'T2', 'T3', 'T4', 'T8'})
        self.assertEqual(float(rows['T1'][2]), 50.0)
        self.assertIsNone(rows['T1'][3])                                # nothing happened before the period


@tagged('post_install', '-at_install')
class TestSameFiguresAsTheIndicators(DashboardCase):
    """The panels give the same figures as the indicators of the Odoo dashboard (bus.kpi), on the same data."""

    def setUp(self):
        super().setUp()
        self.env['bus.trip.simulator']._simulate(self.route, 'late', day=PAST - 4 * DAY)
        when = datetime.combine(PAST, time(15, 0))
        for ms in (80, 120, 400, 900):
            self.env['bus.perf.sample'].create({'name': 'live', 'ms': ms, 'created': when})
        self.env['bus.sync.audit'].create({'total': 50, 'matched': 49, 'run_at': when})
        self.metrics_ = by_code(self.kpi.compute(date_from=self.period['date_from'], date_to=self.period['date_to']))
        self.board = self.boards['01-resumen']

    def panel_value(self, code):
        panel = next(p for p in panels(self.board) if p['title'].startswith(code + ' '))
        value = self.query(self.board, panel['targets'][0]['rawSql'])[0][0]
        return None if value is None else round(float(value), 1)

    def test_the_figures_of_the_transport_indicators_match(self):
        for code in ('T1', 'T2', 'T3', 'T4', 'T5', 'T8'):
            expected = self.metrics_[code]['value']
            self.assertIsNotNone(expected, code)
            self.assertEqual(self.panel_value(code), round(float(expected), 1), code)

    def test_the_two_that_are_judged_on_a_difference_show_that_difference(self):
        self.assertEqual(self.panel_value('T6'), abs(self.metrics_['T6']['value']))
        trips = self.env['bus.trip'].search([('state', '=', 'done'), ('duration_real_min', '>', 0),
                                             ('date', '>=', self.period['date_from']), ('date', '<=', PAST)])
        real = sum(trips.mapped('duration_real_min')) / len(trips)
        planned = sum(trips.mapped('duration_est_min')) / len(trips)
        self.assertEqual(self.panel_value('T7'), round(abs((real - planned) / planned * 100.0), 1))

    def test_the_figures_of_the_software_indicators_match(self):
        for code in ('S1', 'S2', 'S3', 'S4'):
            expected = self.metrics_[code]['value']
            self.assertIsNotNone(expected, code)
            self.assertEqual(self.panel_value(code), round(float(expected), 1), code)
