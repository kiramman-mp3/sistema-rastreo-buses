import base64
import binascii
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .geo import compact
from .gpx import GpxError, parse_gpx

MAX_POINTS = 1500
STOP_RADIUS = 50

class BusRouteGpx(models.TransientModel):
    _name = 'bus.route.gpx'
    _description = 'Load the track of a route from a GPX file'

    route_id = fields.Many2one('bus.route', required=True, ondelete='cascade')
    gpx_file = fields.Binary(string="GPX file", required=True)
    gpx_filename = fields.Char()
    has_stops = fields.Boolean(compute='_compute_has_stops')
    create_stops = fields.Boolean(
        string="Create the stops from the waypoints",
        help="Each named point of the file becomes a stop, in the order of the file. "
             "Only offered while the route has no stops.")

    @api.depends('route_id.stop_ids')
    def _compute_has_stops(self):
        for wizard in self:
            wizard.has_stops = bool(wizard.route_id.stop_ids)

    def action_load(self):
        self.ensure_one()
        if not self.env.user.has_group('bus_tracking.group_bus_manager'):
            raise AccessError(_("Only managers can load a track."))
        try:
            line, waypoints = parse_gpx(base64.b64decode(self.gpx_file or b'', validate=False))
        except binascii.Error:
            raise UserError(_("The file is not a valid GPX file."))
        except GpxError as error:
            # literal strings, so the translation export finds them
            raise UserError({
                'too_big': _("The file is too big (5 MB at most)."),
                'not_xml': _("The file is not a valid GPX file."),
                'not_gpx': _("The file is not a GPX file."),
                'no_line': _("The file has no track or route with at least two points."),
            }[error.code])
        points = compact(line, max_points=MAX_POINTS)
        if len(points) > MAX_POINTS:
            raise UserError(_("The track has %s points after simplifying. Use a shorter file.", len(points)))
        route = self.route_id
        route.track_json = json.dumps([[round(lat, 6), round(lon, 6)] for lat, lon in points],
                                      separators=(',', ':'))
        made = 0
        if self.create_stops and not route.stop_ids:
            for i, (name, lat, lon) in enumerate(waypoints, start=1):
                self.env['bus.route.stop'].create({
                    'route_id': route.id, 'sequence': i * 10, 'radius': STOP_RADIUS,
                    'name': (name or _("Stop %s", i))[:128], 'latitude': round(lat, 7), 'longitude': round(lon, 7)})
                made += 1
        message = _("%(points)s points from %(total)s.", points=len(points), total=len(line))
        if made:
            message += " " + _("%s stops created.", made)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Track loaded"),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
