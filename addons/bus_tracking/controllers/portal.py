import json
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from odoo import fields, http
from odoo.http import Response, request

from ..models.utils import brand_name, fold, map_center, public_contact
from ..models.portal_i18n import STRINGS, pick_lang

# A bus that has not reported for this long is not shown to passengers.
SHOW_BUSES_FOR = timedelta(minutes=15)
CACHE_SECONDS = 5
RATE_LIMIT = 60          # requests per IP and window, per worker process
RATE_WINDOW = 60.0
LANG_COOKIE = 'bus_lang'
# The only strings the page's script needs.
JS_STRINGS = ('status_moving', 'status_stopped', 'status_offline', 'updated', 'update_error', 'stops', 'path_all',
              'live', 'searching', 'updated_min', 'stale', 'rate', 'mine_tag', 'bus_at_mine', 'bus_one_stop',
              'bus_n_stops', 'none_coming', 'position_unknown', 'bus_between', 'bus_at', 'no_buses',
              'featured_hint', 'pick_stop_hint')


def js_strings(strings):
    return json.dumps({key: strings[key] for key in JS_STRINGS})

_HEX_COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')


_STATIC = os.path.join(os.path.dirname(__file__), os.pardir, 'static', 'src')
_VERSIONED = ('css/brand.css', 'portal/site.css', 'portal/pages.css', 'portal/site.js', 'portal/portal_map.js',
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
    values.update(lang=lang, s=STRINGS[lang], asset_v=asset_version(), line_i18n=js_strings(STRINGS[lang]),
                  brand=brand_name(request.env(su=True)),
                  contact=public_contact(request.env(su=True)),
                  languages={c: s['lang_name'] for c, s in STRINGS.items()})
    return values


def render_portal(template, values, status=200):
    response = request.render(template, values)
    response.status_code = status
    if request.params.get('lang') in STRINGS:
        response.set_cookie(LANG_COOKIE, values['lang'], max_age=365 * 24 * 3600, samesite='Lax')
    return response


# An arrival older than this does not say where the bus is now on the line.
ARRIVAL_MEMORY = timedelta(hours=3)


def line_positions(route, buses):
    """Where each bus is on the drawn line, as stop indexes: `at` when it is inside a stop's radius,
    `after` for the last stop it reached (it is between that stop and the next). Only indexes leave
    the server: no times, no ids."""
    index = {stop.id: i for i, stop in enumerate(route.stop_ids)}
    since = fields.Datetime.now() - ARRIVAL_MEMORY
    arrivals = route.env['bus.stop.arrival'].sudo().search(
        [('vehicle_id', 'in', buses.ids), ('stop_id', 'in', route.stop_ids.ids), ('arrival_time', '>=', since)],
        order='arrival_time desc')
    last = {}
    for arrival in arrivals:
        last.setdefault(arrival.vehicle_id.id, index.get(arrival.stop_id.id))
    positions = {}
    for bus in buses:
        at = index.get(bus.current_stop_id.id) if bus.current_stop_id else None
        positions[bus.id] = (at, at if at is not None else last.get(bus.id))
    return positions


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
    @http.route(['/rutas', '/transporte/rutas'], type='http', auth='public', methods=['GET'])
    def routes(self, q=None, **kwargs):
        routes = public_routes()
        query = (q or '').strip()[:80]
        if query:
            needle = fold(query)
            routes = routes.filtered(
                lambda r: needle in fold(r.name) or needle in fold(r.code)
                or any(needle in fold(stop.name) for stop in r.stop_ids))
        total_active_buses = 0
        items = []
        for r in routes:
            fresh_count = len(self._fresh_buses(r))
            total_active_buses += fresh_count
            items.append({
                'code': r.code,
                'name': r.name,
                'color': safe_color(r.color),
                'buses': fresh_count,
                'stops_count': len(r.stop_ids),
                'first_stop': r.stop_ids[:1].name or '',
                'last_stop': r.stop_ids[-1:].name or '',
                'matching_stops': [s.name for s in r.stop_ids if query and fold(query) in fold(s.name)][:3],
            })
        return render_portal('bus_tracking.portal_routes', portal_context(
            routes=items, total_active_buses=total_active_buses, query=query, active_nav='rutas'))

    @http.route(['/rutas/detalle', '/transporte/rutas/detalle'], type='http', auth='public', methods=['GET'])
    def route_detail_alias(self, **kwargs):
        first = public_routes()[:1]
        if first:
            return request.redirect('/rutas/%s' % first.code)
        return request.redirect('/rutas')

    @http.route(['/rutas/<string:code>', '/transporte/rutas/<string:code>'], type='http', auth='public', methods=['GET'])
    def route_map(self, code, **kwargs):
        route = self._public_route(code)
        if not route:
            return request.not_found()
        stops = [{'name': s.name, 'lat': s.latitude, 'lon': s.longitude} for s in route.stop_ids]
        buses = self._fresh_buses(route)
        values = portal_context(
            route={
                'code': route.code,
                'name': route.name,
                'color': safe_color(route.color),
                'buses_count': len(buses),
                'stops': [s['name'] for s in stops],
                'stops_json': json.dumps([s['name'] for s in stops]),
            },
            active_nav='rutas',
            stops=stops,
            stops_json=json.dumps(stops),
            paths_json=json.dumps(route._map_lines(), separators=(',', ':'))
        )
        values['json_i18n'] = values['line_i18n']
        values['center_json'] = json.dumps(list(map_center(request.env(su=True))))
        return render_portal('bus_tracking.portal_route', values)

    @http.route(['/rutas/<string:code>/buses.json', '/transporte/rutas/<string:code>/buses.json'], type='http', auth='public', methods=['GET'])
    def route_buses(self, code, **kwargs):
        if not limiter.allow(request.httprequest.remote_addr):
            return Response(status=429, headers=[('Retry-After', '30')])
        body = cache.get(code)
        if body is None:
            route = self._public_route(code)
            if not route:
                return request.not_found()
            buses = self._fresh_buses(route)
            where = line_positions(route, buses)
            body = json.dumps({
                'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'buses': [{
                    'name': bus.name,
                    'lat': bus.last_latitude,
                    'lon': bus.last_longitude,
                    'course': round(bus.last_course),
                    'status': bus.status if bus.connected else 'offline',
                    'at': where[bus.id][0],
                    'after': where[bus.id][1],
                } for bus in buses],
            })
            cache.put(code, body)
        return Response(body, content_type='application/json',
                        headers=[('Cache-Control', 'public, max-age=%d' % CACHE_SECONDS)])
