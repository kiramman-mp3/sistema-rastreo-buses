import importlib.util
from pathlib import Path

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFinesRealCleanup(TransactionCase):
    """16.0.1.11.0 drops the switch that presented the fines as a demonstration."""

    def migrate(self):
        path = Path(__file__).resolve().parents[1] / 'migrations' / '16.0.1.11.0' / 'post-migrate.py'
        spec = importlib.util.spec_from_file_location('post_migrate_fines', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, '16.0.1.10.0')

    def parameter(self):
        self.env.cr.execute("SELECT value FROM ir_config_parameter WHERE key = 'bus_tracking.fines_real'")
        return self.env.cr.fetchone()

    def test_the_old_parameter_is_removed(self):
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.fines_real', 'True')
        self.migrate()
        self.assertIsNone(self.parameter())

    def test_without_the_parameter_nothing_fails(self):
        self.migrate()
        self.assertIsNone(self.parameter())
