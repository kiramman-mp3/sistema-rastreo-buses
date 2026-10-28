from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from ..models.utils import map_center


class BusStops(http.Controller):
    """Data and saving for the map where a manager picks the point of a stop."""

    @http.route('/bus_tracking/stop/load', type='json', auth='user')
    def load(self, route_id, stop_id=None):
        if not request.env.user.has_group('bus_tracking.group_bus_manager'):
            raise AccessError(_("Only managers can edit stops."))
        route = request.env['bus.route'].browse(int(route_id)).exists()
        if not route:
            return {'error': _("That route no longer exists.")}
        stops = [{'id': s.id, 'name': s.name, 'lat': s.latitude, 'lon': s.longitude, 'radius': s.radius}
                 for s in route.stop_ids]
        return {
            'route': route.name,
            'color': route.color or '#3388ff',
            'stops': stops,
            'lines': route._map_lines(),
            'center': list(map_center(request.env)),
            'stop': next((s for s in stops if s['id'] == int(stop_id or 0)), None),
        }

    @http.route('/bus_tracking/stop/save', type='json', auth='user')
    def save(self, route_id, stop_id, name, latitude, longitude, radius):
        stop = request.env['bus.route.stop']._save_from_map(route_id, stop_id, name, latitude, longitude, radius)
        return {'id': stop.id}
