from pathlib import Path

import psycopg2
from odoo.models import BaseModel
from odoo.tests import tagged
from odoo.tools import mute_logger

from ..models.bus_kpi_views import ORDER, ROLE, VIEWS
from .test_kpi import KpiCase

ROLE_SQL = Path(__file__).resolve().parents[1] / 'data' / 'grafana-role.sql'

# what a person typed or what identifies one: never in a view that leaves for another tool
PERSONAL = {'plate', 'driver', 'driver_id', 'user_id', 'login', 'email', 'phone', 'note', 'password', 'name'}


class ViewCase(KpiCase):
    as_role = False

    def rows(self, sql, *args):
        if not self.as_role:
            self.env.flush_all()                    # the views read the database: write what the ORM still holds
        self.env.cr.execute(sql, args)
        return self.env.cr.fetchall()

    def columns(self, view):
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (view,))
        return {r[0] for r in self.env.cr.fetchall()}


@tagged('post_install', '-at_install')
class TestKpiViews(ViewCase):

    def test_every_view_exists_and_can_be_read(self):
        self.assertEqual(set(ORDER), set(VIEWS))
        for name in ORDER:
            self.rows('SELECT * FROM %s LIMIT 1' % name)

    def test_no_view_carries_personal_data(self):
        for name in ORDER:
            self.assertFalse(self.columns(name) & PERSONAL, name)

    def test_the_trips_are_there_with_their_figures(self):
        rows = {r[0]: r for r in self.rows(
            'SELECT trip_id, state, stops_total, stops_visited, route_code, bus FROM kpi_trips')}
        self.assertEqual(rows[self.trip_a.id][1:4], ('done', 3, 3))
        self.assertEqual(rows[self.trip_c.id][1], 'incomplete')
        self.assertEqual(rows[self.trip_d.id][3], 0)
        self.assertEqual(rows[self.trip_a.id][4], self.route.code)
        self.assertEqual(rows[self.trip_a.id][5], self.bus.name)

    def test_a_trip_that_never_started_still_has_a_time_for_the_filters(self):
        self.assertFalse(self.rows('SELECT 1 FROM kpi_trips WHERE starts_at IS NULL'))

    def test_the_stop_lines_name_the_stop_and_the_local_hour(self):
        rows = self.rows("SELECT stop_name, status, delay_min, local_hour FROM kpi_trip_stops WHERE trip_id = %s "
                         "ORDER BY sequence", self.trip_b.id)
        self.assertEqual([r[0] for r in rows], ['Terminal', 'Plaza', 'Hospital'])
        self.assertEqual([r[1] for r in rows], ['on_time', 'late', 'late'])
        self.assertEqual([round(r[2]) for r in rows], [0, 8, 15])
        planned = self.trip_b.planned_start
        self.assertEqual(rows[0][3], (planned.hour - 5) % 24)

    def test_alerts_and_incidents_share_a_view(self):
        user = self.env['res.users'].create({'name': 'Chofer', 'login': 'views-chofer'})
        shift = self.env['bus.shift'].create({
            'user_id': user.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id,
            'start': self.trip_a.planned_start})
        self.env['bus.incident'].create({
            'shift_id': shift.id, 'vehicle_id': self.bus.id, 'kind': 'breakdown',
            'reported_at': self.trip_a.planned_start})
        total = self.rows('SELECT (SELECT COUNT(*) FROM bus_alert) + (SELECT COUNT(*) FROM bus_incident)')[0][0]
        self.assertEqual(self.rows('SELECT COUNT(*) FROM kpi_alerts')[0][0], total)
        self.assertEqual({r[0] for r in self.rows('SELECT DISTINCT origin FROM kpi_alerts')}, {'alert', 'incident'})

    def test_the_positions_of_a_trip_are_the_ones_inside_its_time(self):
        count = self.rows('SELECT COUNT(*) FROM kpi_positions WHERE trip_id = %s', self.trip_a.id)[0][0]
        self.assertEqual(count, 3)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM kpi_positions WHERE trip_id = %s', self.trip_d.id)[0][0], 0)

    def test_the_software_view_sums_what_the_indicators_use(self):
        for ms in (100, 300):
            self.env['bus.perf.sample'].create({'name': 'live', 'ms': ms})
        self.env['bus.sync.audit'].create({'total': 10, 'matched': 9})
        row = self.rows('SELECT SUM(positions_stored), SUM(audit_matched), SUM(audit_total), SUM(response_samples), '
                        'SUM(simulated_trips) FROM kpi_software')[0]
        self.assertEqual(row[0], self.rows('SELECT COUNT(*) FROM bus_position')[0][0])
        self.assertEqual(row[1:4], (9, 10, 2))
        self.assertEqual(row[4], 0)

    def test_they_are_rebuilt_when_the_module_updates(self):
        self.env.cr.execute('DROP VIEW kpi_software')
        self.env['bus.kpi.views'].init()
        self.rows('SELECT * FROM kpi_software LIMIT 1')
        self.assertIsInstance(self.env['bus.kpi.views'], BaseModel)


@tagged('post_install', '-at_install')
class TestGrafanaRole(ViewCase):
    """The role Grafana connects with. The test creates it inside the transaction, so nothing is left behind."""

    def setUp(self):
        super().setUp()
        cr = self.env.cr
        cr.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        if not cr.fetchone()[0]:
            self.skipTest('needs a database superuser to create a role')
        cr.execute("SELECT current_database()")
        sql = ROLE_SQL.read_text(encoding='utf8').replace('__PASSWORD__', 'test-pass-1').replace(
            '__DB__', cr.fetchone()[0])
        cr.execute(sql)
        self.env.flush_all()
        cr.execute('SET LOCAL ROLE "%s"' % ROLE)
        self.as_role = True
        self.addCleanup(self.back_to_odoo)

    def back_to_odoo(self):
        self.as_role = False
        self.env.cr.execute('RESET ROLE')

    def denied(self, sql):
        cr = self.env.cr
        cr.execute('SAVEPOINT denied')
        with mute_logger('odoo.sql_db'):
            try:
                cr.execute(sql)
            except psycopg2.errors.InsufficientPrivilege:
                cr.execute('ROLLBACK TO SAVEPOINT denied')
                return
        self.fail('should have been refused: ' + sql)

    def test_it_reads_the_views(self):
        for name in ORDER:
            self.rows('SELECT * FROM %s LIMIT 1' % name)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM kpi_trips')[0][0], 4)

    def test_it_cannot_read_the_tables_of_odoo(self):
        for table in ('bus_trip', 'bus_position', 'res_users', 'res_partner', 'bus_incident', 'ir_config_parameter'):
            self.denied('SELECT * FROM %s LIMIT 1' % table)

    def test_it_cannot_write(self):
        self.denied("UPDATE kpi_routes SET color = 'x'")
        self.denied("INSERT INTO bus_route (name, code) VALUES ('x', 'x')")
        self.denied('DELETE FROM kpi_routes')
        self.denied('CREATE TABLE grafana_probe (id int)')

    def test_it_is_configured_to_be_read_only_and_limited(self):
        self.env.cr.execute('RESET ROLE')
        self.env.cr.execute("""SELECT rolconnlimit, rolsuper, rolcreaterole, rolcreatedb, rolreplication,
                                      (SELECT array_agg(c) FROM unnest(setconfig) c)
                                 FROM pg_roles r
                                 LEFT JOIN pg_db_role_setting s ON s.setrole = r.oid AND s.setdatabase = 0
                                WHERE rolname = %s""", (ROLE,))
        limit, superuser, createrole, createdb, replication, settings = self.env.cr.fetchone()
        self.assertEqual((limit, superuser, createrole, createdb, replication), (5, False, False, False, False))
        self.assertIn('default_transaction_read_only=on', settings)
        self.assertIn('statement_timeout=10s', settings)
        self.env.cr.execute('SET LOCAL ROLE "%s"' % ROLE)

    def test_running_the_script_twice_is_harmless(self):
        self.env.cr.execute('RESET ROLE')
        self.env.cr.execute("SELECT current_database()")
        sql = ROLE_SQL.read_text(encoding='utf8').replace('__PASSWORD__', 'another-pass-2').replace(
            '__DB__', self.env.cr.fetchone()[0])
        self.env.cr.execute(sql)
        self.env.cr.execute('SET LOCAL ROLE "%s"' % ROLE)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM kpi_trips')[0][0], 4)
