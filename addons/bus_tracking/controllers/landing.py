from odoo import http
from odoo.addons.web.controllers.home import Home
from odoo.http import request

from ..models.utils import brand_name
from .portal import asset_version


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
        return {'asset_v': asset_version(), 'brand': brand_name(request.env(su=True))}
