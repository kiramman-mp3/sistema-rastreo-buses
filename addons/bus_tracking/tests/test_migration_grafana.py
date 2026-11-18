import importlib.util
from pathlib import Path

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestGrafanaRemoval(TransactionCase):
    """16.0.1.9.0 removes what Grafana left in the database: its views, its daily counts and its role."""

    def migrate(self):
        path = Path(__file__).resolve().parents[1] / 'migrations' / '16.0.1.9.0' / 'pre-migrate.py'
        spec = importlib.util.spec_from_file_location('pre_migrate_grafana', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, '16.0.1.8.0')

    def exists(self, query, value):
        self.env.cr.execute(query, (value,))
        return bool(self.env.cr.fetchone())

    def test_the_role_that_owns_grants_is_dropped(self):
        """The role had read grants; on Supabase only a member of the role may drop them (DEF-076)."""
        cr = self.env.cr
        cr.execute("SELECT 1 FROM pg_roles WHERE rolname = 'grafana_reader'")
        if not cr.fetchone():
            cr.execute('CREATE ROLE grafana_reader NOLOGIN')
        cr.execute('GRANT SELECT ON bus_vehicle TO grafana_reader')
        cr.execute('CREATE VIEW kpi_extra AS SELECT 1 AS one')
        cr.execute("INSERT INTO ir_config_parameter (key, value) VALUES ('bus_tracking.grafana_url', 'x')")
        self.migrate()
        self.assertFalse(self.exists("SELECT 1 FROM pg_roles WHERE rolname = %s", 'grafana_reader'))
        self.assertFalse(self.exists("SELECT 1 FROM pg_views WHERE viewname = %s", 'kpi_extra'))
        self.assertFalse(self.exists("SELECT 1 FROM ir_config_parameter WHERE key = %s", 'bus_tracking.grafana_url'))

    def test_without_the_role_nothing_fails(self):
        self.migrate()
        self.assertFalse(self.exists("SELECT 1 FROM pg_roles WHERE rolname = %s", 'grafana_reader'))
