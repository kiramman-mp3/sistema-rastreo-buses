from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

KINDS = [
    ('breakdown', "Breakdown"),
    ('traffic', "Traffic"),
    ('accident', "Accident"),
    ('other', "Other"),
    ('sos', "Emergency (SOS)"),
]


class BusIncident(models.Model):
    _name = 'bus.incident'
    _description = 'Driver Incident'
    _order = 'create_date desc, id desc'

    shift_id = fields.Many2one('bus.shift', required=True, ondelete='cascade', index=True)
    vehicle_id = fields.Many2one('bus.vehicle', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one(related='shift_id.user_id', store=True, index=True)
    route_id = fields.Many2one(related='shift_id.route_id', store=True, index=True)
    kind = fields.Selection(KINDS, required=True, index=True)
    note = fields.Char()
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    notified = fields.Boolean(default=False, index=True)
    acknowledged_by = fields.Many2one('res.users', string="Seen by", readonly=True, copy=False)
    acknowledged_at = fields.Datetime(string="Seen at", readonly=True, copy=False, index=True)
    state = fields.Selection([('open', "Open"), ('seen', "Seen")], compute='_compute_state', store=True,
                             string="State", index=True)

    @api.depends('acknowledged_at')
    def _compute_state(self):
        for incident in self:
            incident.state = 'seen' if incident.acknowledged_at else 'open'

    def action_acknowledge(self):
        """Someone in the office saw it. The driver's tablet shows who and when."""
        if not self.env.user.has_group('bus_tracking.group_bus_user'):
            raise AccessError(_("Only the transport team can mark an incident as seen."))
        pending = self.filtered(lambda i: not i.acknowledged_at)
        pending.sudo().write({'acknowledged_by': self.env.user.id, 'acknowledged_at': fields.Datetime.now()})
        return True

    @api.model
    def _open_for_map(self, hours=24):
        since = fields.Datetime.now() - timedelta(hours=hours)
        return self.search([('acknowledged_at', '=', False), ('create_date', '>=', since)],
                           order='create_date desc', limit=50)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(r.kind == 'sos' for r in records):
            # An emergency must not wait for the next minute of the cron.
            cron = self.env.ref('bus_tracking.cron_push_incidents', raise_if_not_found=False)
            if cron:
                cron.sudo()._trigger()
        return records

    @api.model
    def _cron_push(self):
        """Tell the managers about new incidents. Same channel as bus.alert: a slow
        push service must not delay the tablet HTTP response."""
        pending = self.search([('notified', '=', False)], limit=50)
        if not pending:
            return
        push = self.env['bus.push.subscription']
        labels = dict(self._fields['kind']._description_selection(self.env))
        for incident in pending:
            payload = {
                'title': '%s: %s' % (labels.get(incident.kind, incident.kind), incident.vehicle_id.name),
                'body': incident.note or '',
                'url': '/web#id=%d&model=bus.incident&view_type=form' % incident.id,
                'tag': 'bus-incident',
            }
            push._send_to_managers(payload)
        pending.write({'notified': True})
