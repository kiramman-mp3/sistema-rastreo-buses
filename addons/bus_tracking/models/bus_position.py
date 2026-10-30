from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BusPosition(models.Model):
    _name = 'bus.position'
    _description = 'Bus Position'
    _order = 'fix_time desc, id desc'

    vehicle_id = fields.Many2one('bus.vehicle', required=True, ondelete='cascade', index=True)
    fix_time = fields.Datetime(required=True, index=True)
    latitude = fields.Float(digits=(10, 7), required=True)
    longitude = fields.Float(digits=(10, 7), required=True)
    speed = fields.Float(help="km/h")
    course = fields.Float(help="Heading in degrees.")
    altitude = fields.Float()
    address = fields.Char()

    _sql_constraints = [
        ('vehicle_fix_uniq', 'unique(vehicle_id, fix_time)', "Duplicate position for this bus and time."),
    ]

    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for rec in self:
            if not (-90.0 <= rec.latitude <= 90.0 and -180.0 <= rec.longitude <= 180.0):
                raise ValidationError(_("Latitude must be between -90 and 90, and longitude between -180 and 180."))

    @api.model
    def _cron_cleanup(self):
        icp = self.env['ir.config_parameter'].sudo()
        days = int(icp.get_param('bus_tracking.retention_days') or 0)
        if days <= 0:
            return
        limit = fields.Datetime.now() - timedelta(days=days)
        self.search([('fix_time', '<', limit)]).unlink()
