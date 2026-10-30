from odoo import fields, models

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
    kind = fields.Selection(KINDS, required=True, index=True)
    note = fields.Char()
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
