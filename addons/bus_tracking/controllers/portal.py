import json
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from odoo import fields, http
from odoo.http import Response, request

from ..models.utils import brand_name, float_to_clock, local_now, map_center
from ..models.portal_i18n import STRINGS, pick_lang

# A bus that has not reported for this long is not shown to passengers.
SHOW_BUSES_FOR = timedelta(minutes=15)
CACHE_SECONDS = 5
RATE_LIMIT = 60          # requests per IP and window, per worker process
RATE_WINDOW = 60.0
LANG_COOKIE = 'bus_lang'
# The only strings the page's script needs.
JS_STRINGS = ('status_moving', 'status_stopped', 'status_offline', 'updated', 'update_error', 'stops', 'path_all')

_HEX_COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')


_STATIC = os.path.join(os.path.dirname(__file__), os.pardir, 'static', 'src')
_VERSIONED = ('css/brand.css', 'landing/landing.css', 'portal/portal.css', 'portal/portal_map.js',
              'portal/complaint.js')


def asset_version():
    """Changes whenever a public stylesheet or script does, so browsers never keep a stale copy."""
    return str(max(int(os.path.getmtime(os.path.join(_STATIC, name))) for name in _VERSIONED))


def safe_color(value):
    return value if value and _HEX_COLOR.match(value) else '#1e5560'


class RateLimiter:
    """Sliding window per key. In memory, so each worker counts on its own."""

    def __init__(self, limit, window):
        self.limit, self.window = limit, window
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key, now=None):
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self):
        with self._lock:
            self._hits.clear()


class TtlCache:
    def __init__(self, ttl):
        self.ttl = ttl
        self._items = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._items.get(key)
            if item and time.monotonic() - item[0] < self.ttl:
                return item[1]

    def put(self, key, value):
        with self._lock:
            self._items[key] = (time.monotonic(), value)

    def clear(self):
        with self._lock:
            self._items.clear()


limiter = RateLimiter(RATE_LIMIT, RATE_WINDOW)
cache = TtlCache(CACHE_SECONDS)


def portal_context(**values):
    lang = pick_lang(
        request.httprequest.accept_languages,
        requested=request.params.get('lang'),
        remembered=request.httprequest.cookies.get(LANG_COOKIE))
    values.update(lang=lang, s=STRINGS[lang], asset_v=asset_version(),
                  brand=brand_name(request.env(su=True)),
                  languages={c: s['lang_name'] for c, s in STRINGS.items()})
    return values


def render_portal(template, values, status=200):
    response = request.render(template, values)
    response.status_code = status
    if request.params.get('lang') in STRINGS:
        response.set_cookie(LANG_COOKIE, values['lang'], max_age=365 * 24 * 3600, samesite='Lax')
    return response


def build_timetable(route):
    """The schedules of the buses of a line that have not left yet today."""
    now = local_now(request.env(su=True))
    hour = now.hour + now.minute / 60.0
    schedules = request.env(su=True)['bus.schedule'].search([('route_id', '=', route.id)], order='departure, id')
    return {
        'no_service': not schedules,
        'as_of': '%02d:%02d' % (now.hour, now.minute),
        'items': [{'dep': float_to_clock(item.departure), 'arr': float_to_clock(item.arrival), 'bus': item.vehicle_id.name}
                  for item in schedules if item.departure >= hour - 5 / 60.0],
    }


def public_routes():
    return request.env(su=True)['bus.route'].search([('active', '=', True), ('public', '=', True)])


class BusPortal(http.Controller):
    """Public pages for passengers. They only ever read, and they only expose
    the bus name, position, heading and status: never plate, driver, speed,
    identifiers or history."""

    def _public_route(self, code):
        return request.env(su=True)['bus.route'].search(
            [('code', '=', code), ('active', '=', True), ('public', '=', True)], limit=1)

    @staticmethod
    def _fresh_buses(route):
        limit = fields.Datetime.now() - SHOW_BUSES_FOR
        return route.vehicle_ids.filtered(lambda b: b.last_fix_time and b.last_fix_time >= limit)

    # ------------------------------------------------------------------
    @http.route('/rutas', type='http', auth='public', methods=['GET'])
    def routes(self, **kwargs):
        routes = public_routes()
        items = [{
            'code': r.code,
            'name': r.name,
            'color': safe_color(r.color),
            'buses': len(self._fresh_buses(r)),
        } for r in routes]
        return render_portal('bus_tracking.portal_routes', portal_context(routes=items))

    @http.route('/rutas/<string:code>', type='http', auth='public', methods=['GET'])
    def route_map(self, code, **kwargs):
        route = self._public_route(code)
        if not route:
            return request.not_found()
        stops = [{'name': s.name, 'lat': s.latitude, 'lon': s.longitude} for s in route.stop_ids]
        values = portal_context(
            route={'code': route.code, 'name': route.name, 'color': safe_color(route.color)},
            stops_json=json.dumps(stops), paths_json=json.dumps(route._map_lines(), separators=(',', ':')))
        values['json_i18n'] = json.dumps({key: values['s'][key] for key in JS_STRINGS})
        values['center_json'] = json.dumps(list(map_center(request.env(su=True))))
        values['timetable'] = build_timetable(route)
        return render_portal('bus_tracking.portal_route', values)

    @http.route('/rutas/<string:code>/buses.json', type='http', auth='public', methods=['GET'])
    def route_buses(self, code, **kwargs):
        if not limiter.allow(request.httprequest.remote_addr):
            return Response(status=429, headers=[('Retry-After', '30')])
        body = cache.get(code)
        if body is None:
            route = self._public_route(code)
            if not route:
                return request.not_found()
            body = json.dumps({
                'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'buses': [{
                    'name': bus.name,
                    'lat': bus.last_latitude,
                    'lon': bus.last_longitude,
                    'course': round(bus.last_course),
                    'status': bus.status,
                } for bus in self._fresh_buses(route)],
            })
            cache.put(code, body)
        return Response(body, content_type='application/json',
                        headers=[('Cache-Control', 'public, max-age=%d' % CACHE_SECONDS)])
