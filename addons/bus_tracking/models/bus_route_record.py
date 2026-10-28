import json
from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError

from .geo import simplify, thin

MIN_GAP_M = 10          # points closer than this are the same place
TOLERANCE_M = 8         # the simplified line stays within this distance of the recorded one
MAX_POINTS = 1500


class BusRouteRecord(models.TransientModel):
    _name = 'bus.route.record'
    _description = 'Record the track of a route from a bus'

    route_id = fields.Many2one('bus.route', required=True, ondelete='cascade')
    vehicle_id = fields.Many2one('bus.vehicle', string="Bus", required=True)
    date_from = fields.Datetime(string="From", required=True, default=lambda self: fields.Datetime.now() - timedelta(hours=2))
    date_to = fields.Datetime(string="Until", required=True, default=fields.Datetime.now)

    def action_record(self):
        self.ensure_one()
        positions = self.env['bus.position'].search([
            ('vehicle_id', '=', self.vehicle_id.id),
            ('fix_time', '>=', self.date_from), ('fix_time', '<=', self.date_to)], order='fix_time asc')
        points = simplify(thin([(p.latitude, p.longitude) for p in positions], MIN_GAP_M), TOLERANCE_M)
        if len(points) < 2:
            raise UserError(_("That bus has too few positions in this period to draw a track."))
        if len(points) > MAX_POINTS:
            raise UserError(_("The track has %s points after simplifying. Choose a shorter period.", len(points)))
        self.route_id.track_json = json.dumps([[round(lat, 6), round(lon, 6)] for lat, lon in points],
                                              separators=(',', ':'))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Track recorded"),
                'message': _("%(points)s points from %(positions)s positions.", points=len(points), positions=len(positions)),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
