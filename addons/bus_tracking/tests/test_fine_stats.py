from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .test_driver_auth import make_driver
from .test_fine_detect import FineCase, simulate


@tagged('post_install', '-at_install')
class TestFineStats(FineCase):
    """The fines in the dashboard and in the PDF report: by state, driver, type and week, and the precision."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other = make_driver(cls.env, login='chofer_stats')
        Fine = cls.env['bus.fine']
        speeding = Fine.search([('trip_id', '=', simulate(cls.env, cls.route, 'speeding', cls.driver, 1).id)])
        deviation = Fine.search([('trip_id', '=', simulate(cls.env, cls.route, 'deviation', cls.driver, 2).id)])
        skipped = Fine.search([('trip_id', '=', simulate(cls.env, cls.route, 'skipped_stop', cls.other, 3).id)])
        Fine.search([('trip_id', '=', simulate(cls.env, cls.route, 'not_started', cls.other, 4).id)])
        speeding.action_fine()
        deviation.action_fine()
        deviation._appeal('Desvío por obra')
        skipped._discard('gps')
        cls.today = fields.Date.context_today(cls.env['bus.fine'])

    def stats(self, **kw):
        return self.env['bus.fine']._dashboard(self.today - timedelta(days=10), self.today, **kw)

    def test_by_state_and_metrics(self):
        data = self.stats()
        self.assertEqual(data['by_state'], {'new': 0, 'review': 0, 'fined': 1, 'appealed': 1, 'discarded': 2})
        metrics = {m['code']: m['value'] for m in data['metrics']}
        self.assertEqual(metrics['F1'], 3)                     # the system filtered out the trip without GPS
        self.assertEqual(metrics['F2'], 1)                     # the appeal waits for a decision
        self.assertEqual(metrics['F3'], 45.0)                  # 25 + 20
        self.assertEqual(metrics['F4'], round(100 * 2 / 3, 1))   # 2 confirmed, 1 discarded by a person
        self.assertEqual(metrics['F5'], 1)
        self.assertEqual(data['currency'], '$')

    def test_by_driver_and_type(self):
        data = self.stats()
        first = data['by_driver'][0]
        self.assertEqual((first['driver'], first['fined'], first['appealed'], first['amount']),
                         (self.driver.name, 1, 1, 45.0))
        types = {row['rule']: row for row in data['by_type']}
        self.assertEqual(types['skipped_stop']['precision'], 0.0)
        self.assertEqual(types['speeding']['precision'], 100.0)
        self.assertIsNone(types['late_start']['precision'])      # only the system decided on it
        self.assertEqual(types['late_start']['by_system'], 1)
        self.assertEqual(sum(sum(week[s] for s in data['states']) for week in data['by_week']), 4)
        self.assertEqual(len(data['points']), 4)

    def test_filters_of_the_dashboard(self):
        self.assertFalse(self.stats(scope='real')['by_driver'])
        self.assertEqual(len(self.stats(scope='simulated')['points']), 4)
        other = self.env['bus.route'].create({'name': 'Otra', 'code': 'OT'})
        self.assertFalse(self.stats(routes=[other.id])['points'])
        old = self.env['bus.fine']._dashboard(self.today - timedelta(days=60), self.today - timedelta(days=30))
        self.assertFalse(old['points'])

    def test_the_dashboard_and_the_report_carry_the_fines(self):
        data = self.env['bus.kpi'].dashboard(str(self.today - timedelta(days=10)), str(self.today), compare=False)
        self.assertEqual(data['fines']['by_state']['fined'], 1)
        wizard = self.env['bus.report.wizard'].create({'date_from': self.today - timedelta(days=10),
                                                       'date_to': self.today, 'scope': 'all'})
        html = self.env['ir.actions.report']._render_qweb_html('bus_tracking.report_operation', wizard.ids)[0]
        self.assertIn(b'Fines by driver', html)
        self.assertIn(self.driver.name.encode(), html)
