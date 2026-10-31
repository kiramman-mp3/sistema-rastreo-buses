from datetime import timedelta
from odoo import fields, http
from odoo.addons.web.controllers.home import Home
from odoo.http import request

from ..models.utils import brand_name
from .portal import asset_version, SHOW_BUSES_FOR, safe_color


class BusLanding(Home):

    @http.route('/', type='http', auth='none')
    def index(self, *args, **kw):
        # Visitors without a session see the landing; signed-in users go to the backend as usual.
        if request.db and not request.session.uid:
            return request.render('bus_tracking.landing', self._values())
        return super().index(*args, **kw)

    @http.route('/inicio', type='http', auth='none')
    def landing(self, **kw):
        if not request.db:
            return request.redirect('/web/database/selector')
        return request.render('bus_tracking.landing', self._values())

    def _values(self):
        env = request.env(su=True)
        routes = env['bus.route'].search([('active', '=', True), ('public', '=', True)])
        now = fields.Datetime.now()
        route_list = []
        for r in routes:
            fresh = r.vehicle_ids.filtered(
                lambda b: b.connected or (b.last_fix_time and (now - b.last_fix_time) <= SHOW_BUSES_FOR)
            )
            route_list.append({
                'id': r.id,
                'code': r.code,
                'name': r.name,
                'color': safe_color(r.color),
                'buses_count': len(fresh),
            })

        stops = env['bus.route.stop'].search([], order='sequence, id')
        unique_stops = []
        seen = set()
        for s in stops:
            name = (s.name or '').strip()
            if name and name not in seen:
                seen.add(name)
                unique_stops.append(name)

        return {
            'asset_v': asset_version(),
            'brand': brand_name(env),
            'routes': route_list,
            'stops': unique_stops,
        }
