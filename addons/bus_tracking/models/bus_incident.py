from odoo import api, fields, models

KINDS = [
    ('breakdown', "Breakdown"),
    ('traffic', "Traffic"),
    ('accident', "Accident"),
    ('other', "Other"),
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
