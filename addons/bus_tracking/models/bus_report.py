"""The operation report as a PDF: the same figures as the dashboard, for a period, some lines and real or simulated
data, laid out to be printed or sent."""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .bus_trip import utc_to_local_date
from .utils import brand_name

# Lower is better for these: a rise is bad news (the same set as the dashboard).
LOWER_IS_BETTER = {'T3', 'T5', 'T8', 'S3'}
MAX_DAYS = 366


def _today(env):
    return utc_to_local_date(fields.Datetime.now())


class BusReportWizard(models.TransientModel):
    _name = 'bus.report.wizard'
    _description = 'Download the operation report'

    date_from = fields.Date(string="From", required=True, default=lambda self: _today(self.env) - timedelta(days=29))
    date_to = fields.Date(string="To", required=True, default=lambda self: _today(self.env))
    route_ids = fields.Many2many('bus.route', string="Lines", help="Empty: every line.")
    scope = fields.Selection([('all', "Real and simulated data"), ('real', "Real data only"),
                              ('simulated', "Simulated data only")], string="Data", required=True, default='real')
    compare = fields.Boolean(string="Compare with the previous period", default=True)

    @api.constrains('date_from', 'date_to')
    def _check_period(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_("The start of the period must come before its end."))
            if (wizard.date_to - wizard.date_from).days >= MAX_DAYS:
                raise UserError(_("The report covers at most one year."))

    def action_print(self):
        self.ensure_one()
        # config=False: the report has its own header, so Odoo must not ask for the company document layout first.
        return self.env.ref('bus_tracking.action_report_operation').report_action(self, config=False)


class BusOperationReport(models.AbstractModel):
    _name = 'report.bus_tracking.report_operation'
    _description = 'Operation report (PDF)'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['bus.report.wizard'].browse(docids).exists()
        if not wizard:
            raise UserError(_("Choose the period of the report again."))
        wizard = wizard[0]
        data = self.env['bus.kpi'].dashboard(wizard.date_from, wizard.date_to, wizard.route_ids.ids or None,
                                             wizard.scope, wizard.compare)
        previous = data.get('previous') or {}
        metrics = []
        for metric in data['metrics']:
            before = previous.get(metric['code'])
            change = trend = None
            if metric['value'] is not None and before is not None:
                change = round(metric['value'] - before, 1)
                if change:
                    better = change < 0 if metric['code'] in LOWER_IS_BETTER else change > 0
                    trend = 'better' if better else 'worse'
            metrics.append(dict(metric, previous=before, change=change, trend=trend))
        by_route = [r for r in data['by_route'] if r['trips'] or r['alerts']]
        by_day = data['by_day']
        kinds = data['incident_kinds']
        labels = data['kind_labels']
        scope_names = dict(self.env['bus.report.wizard']._fields['scope']._description_selection(self.env))
        return {
            'doc_ids': wizard.ids,
            'doc_model': 'bus.report.wizard',
            'docs': wizard,
            'period': data['period'],
            'scope_name': scope_names.get(wizard.scope, wizard.scope),
            'lines_name': ', '.join(wizard.route_ids.mapped('display_name')) or _("Every line"),
            'transport': [m for m in metrics if m['group'] == 'transport'],
            'software': [m for m in metrics if m['group'] != 'transport'],
            'by_route': by_route,
            'by_day': by_day,
            'max_day_trips': max([d['done'] + d['incomplete'] for d in by_day] or [0]) or 1,
            'kinds': [dict(k, label=labels.get(k['kind'], k['kind'])) for k in kinds],
            'max_kind': max([k['count'] for k in kinds] or [0]) or 1,
            'buckets': data['delay_buckets'],
            'max_bucket': max([b['count'] for b in data['delay_buckets']] or [0]) or 1,
            'stop_delays': data['stop_delays'][:10],
            'fines': data['fines'],
            'trips': data['trips'][:25],
            'printed_at': fields.Datetime.context_timestamp(self, fields.Datetime.now()),
            'printed_by': self.env.user.name,
            'brand': brand_name(self.env),
        }
