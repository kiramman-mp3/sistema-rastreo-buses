import json

from odoo import fields, http
from odoo.addons.web.controllers.home import Home
from odoo.http import request

from .portal import SHOW_BUSES_FOR, portal_context, public_routes, render_portal, safe_color


class BusLanding(Home):

    @http.route(['/', '/transporte'], type='http', auth='none')
    def index(self, *args, **kw):
        # Visitors without a session see the landing; signed-in users go to the backend as usual.
        if request.db and not request.session.uid:
            return render_portal('bus_tracking.landing', self._values())
        return super().index(*args, **kw)

    @http.route('/inicio', type='http', auth='none')
    def landing(self, **kw):
        if not request.db:
            return request.redirect('/web/database/selector')
        return render_portal('bus_tracking.landing', self._values())

    def _values(self):
        """The home page shows the lines as they are now. Nothing here is invented: counts come from
        buses that reported in the last 15 minutes, stops from the routes."""
        now = fields.Datetime.now()
        lines = []
        for r in public_routes():
            fresh = r.vehicle_ids.filtered(lambda b: b.last_fix_time and now - b.last_fix_time <= SHOW_BUSES_FOR)
            lines.append({
                'code': r.code,
                'name': r.name,
                'color': safe_color(r.color),
                'buses': len(fresh),
                'stops': [s.name for s in r.stop_ids],
                'stops_json': json.dumps([s.name for s in r.stop_ids]),
            })
        # The line drawn in the first screen: the one with most buses right now, else the first one.
        featured = max(lines, key=lambda line: line['buses']) if lines else None
        return portal_context(
            lines=lines,
            featured=featured,
            featured_json=json.dumps(featured) if featured else '',
            total_buses=sum(line['buses'] for line in lines),
            stop_names=sorted({name for line in lines for name in line['stops']}),
            active_nav='inicio',
        )
