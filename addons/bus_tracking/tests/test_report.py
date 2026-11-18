from datetime import timedelta

from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_kpi import DAY, PAST, KpiCase


@tagged('post_install', '-at_install')
class TestOperationReport(KpiCase):
    """The PDF report: the figures of the dashboard for the period of the wizard, against the trips of KpiCase."""

    def wizard(self, **vals):
        return self.env['bus.report.wizard'].create(dict({
            'date_from': PAST - 5 * DAY, 'date_to': PAST, 'scope': 'all'}, **vals))

    def values(self, wizard):
        return self.env['report.bus_tracking.report_operation']._get_report_values(wizard.ids)

    def test_the_wizard_proposes_the_last_thirty_days(self):
        wizard = self.env['bus.report.wizard'].create({})
        self.assertEqual((wizard.date_to - wizard.date_from).days, 29)
        self.assertEqual(wizard.scope, 'real')

    def test_the_period_must_be_in_order_and_at_most_a_year(self):
        with self.assertRaises(UserError):
            self.wizard(date_from=PAST, date_to=PAST - DAY)
        with self.assertRaises(UserError):
            self.wizard(date_from=PAST - timedelta(days=400))

    def test_printing_goes_straight_to_the_pdf(self):
        """No detour through the company document layout: the report has its own header."""
        action = self.wizard().action_print()
        self.assertEqual(action['type'], 'ir.actions.report')
        self.assertEqual(action['report_name'], 'bus_tracking.report_operation')

    def test_the_report_has_the_figures_of_the_dashboard(self):
        values = self.values(self.wizard())
        codes = [m['code'] for m in values['transport']] + [m['code'] for m in values['software']]
        self.assertEqual(codes, ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'S1', 'S2', 'S3', 'S4'])
        t1 = values['transport'][0]
        self.assertEqual(t1['value'], 50.0)                      # A and B done, C and D incomplete
        row, = [r for r in values['by_route'] if r['id'] == self.route.id]
        self.assertEqual(row['trips'], 4)
        self.assertEqual(values['lines_name'], 'Every line')

    def test_the_change_is_judged_by_the_direction_of_the_indicator(self):
        values = self.values(self.wizard(date_from=PAST - DAY, date_to=PAST))
        t1 = values['transport'][0]                             # A and B done now, nothing done before
        self.assertEqual((t1['previous'], t1['change'], t1['trend']), (0.0, 100.0, 'better'))

    def test_a_line_filter_names_the_line(self):
        values = self.values(self.wizard(route_ids=[(6, 0, self.route.ids)]))
        self.assertEqual(values['lines_name'], self.route.display_name)

    def test_the_html_shows_every_section(self):
        html = self.env['ir.actions.report']._render_qweb_html(
            'bus_tracking.action_report_operation', self.wizard().ids)[0].decode()
        for heading in ('Operation report', 'Transport indicators', 'Lines', 'Day by day', 'Arrivals by delay',
                        'Incidents and alerts by kind', 'Latest trips', 'System quality'):
            self.assertIn(heading, html)
        self.assertIn(self.route.code, html)

    def test_the_menus_say_reports_and_notifications(self):
        self.assertEqual(self.env.ref('bus_tracking.menu_bus_indicators').name, 'Reports')
        self.assertEqual(self.env.ref('bus_tracking.menu_bus_reports').name, 'Notifications')
        self.assertEqual(self.env.ref('bus_tracking.menu_bus_report_pdf').parent_id,
                         self.env.ref('bus_tracking.menu_bus_indicators'))
