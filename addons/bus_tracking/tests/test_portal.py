import json
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged

from ..controllers import portal
from ..models.portal_i18n import STRINGS
from .common import traccar_position


@tagged('post_install', '-at_install')
class TestPassengerPortal(HttpCase):

    def setUp(self):
        super().setUp()
        portal.limiter.reset()
        portal.cache.clear()
        self.route = self.env['bus.route'].create({
            'name': 'Linea Centro', 'code': 'L1', 'color': '#c23327',
            'stop_ids': [(0, 0, {'name': 'Terminal', 'latitude': -33.45, 'longitude': -70.66}),
                         (0, 0, {'name': 'Plaza', 'latitude': -33.46, 'longitude': -70.65})]})
        self.driver = self.env['res.partner'].create({'name': 'Pedro Secreto'})
        self.bus = self.env['bus.vehicle'].create({
            'name': 'Bus 12', 'plate': 'ZZZZ-99', 'route_id': self.route.id, 'driver_id': self.driver.id,
            'traccar_device_id': 5, 'traccar_unique_id': 'b-supersecretid00'})
        self.now = fields.Datetime.now().replace(microsecond=0)

    def report(self, bus, minutes_ago, knots=10.0, device=5):
        when = (self.now - timedelta(minutes=minutes_ago)).strftime('%Y-%m-%dT%H:%M:%SZ')
        bus._apply_position(traccar_position(device, when, -33.455, -70.655, speed_knots=knots))

    def buses(self, code='L1', **kwargs):
        resp = self.url_open('/rutas/%s/buses.json' % code, **kwargs)
        return resp, (resp.json() if resp.status_code == 200 else None)

    # -- pages ---------------------------------------------------------------
    def test_routes_page_lists_only_public_active_routes(self):
        self.env['bus.route'].create({'name': 'Privada', 'code': 'P9', 'public': False})
        self.env['bus.route'].create({'name': 'Archivada', 'code': 'A1', 'active': False})
        html = self.url_open('/rutas').text
        self.assertIn('Linea Centro', html)
        self.assertNotIn('Privada', html)
        self.assertNotIn('Archivada', html)

    def test_routes_page_counts_buses_in_service(self):
        self.assertIn('Sin buses con señal', self.url_open('/rutas').text)
        self.report(self.bus, 1)
        self.assertIn('1 en servicio', self.url_open('/rutas').text)

    def test_route_page_exists_only_for_public_routes(self):
        self.assertEqual(self.url_open('/rutas/L1').status_code, 200)
        self.assertEqual(self.url_open('/rutas/NOPE').status_code, 404)
        self.route.public = False
        self.assertEqual(self.url_open('/rutas/L1').status_code, 404)

    def test_names_are_escaped(self):
        self.route.name = '<script>alert(1)</script>'
        html = self.url_open('/rutas').text
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)

    def test_a_bad_color_cannot_inject_css(self):
        self.route.color = 'red; background:url(//evil)'
        html = self.url_open('/rutas').text
        self.assertIn('#1e5560', html)
        self.assertNotIn('evil', html)

    # -- the public data feed ------------------------------------------------------
    def test_feed_exposes_only_what_passengers_need(self):
        self.report(self.bus, 1, knots=20.0)
        resp, data = self.buses()
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        self.assertEqual(len(data['buses']), 1)
        self.assertEqual(sorted(data['buses'][0]), ['course', 'lat', 'lon', 'name', 'status'])
        self.assertEqual(data['buses'][0]['name'], 'Bus 12')
        self.assertEqual(data['buses'][0]['status'], 'moving')
        for secret in ('ZZZZ-99', 'Pedro Secreto', 'b-supersecretid00', 'speed', 'plate', 'driver'):
            self.assertNotIn(secret, resp.text)

    def test_feed_hides_stale_and_foreign_buses(self):
        stale = self.env['bus.vehicle'].create({'name': 'Viejo', 'route_id': self.route.id, 'traccar_device_id': 6})
        self.report(stale, 16, device=6)
        other_route = self.env['bus.route'].create({'name': 'Otra', 'code': 'L2'})
        foreign = self.env['bus.vehicle'].create({'name': 'Ajeno', 'route_id': other_route.id, 'traccar_device_id': 7})
        self.report(foreign, 1, device=7)
        self.report(self.bus, 2)
        _, data = self.buses()
        self.assertEqual([b['name'] for b in data['buses']], ['Bus 12'])

    def test_feed_marks_a_silent_bus_but_still_shows_it_for_a_while(self):
        self.report(self.bus, 8)
        _, data = self.buses()
        self.assertEqual(data['buses'][0]['status'], 'offline')

    def test_feed_is_404_for_private_or_unknown_routes(self):
        self.assertEqual(self.buses('NOPE')[0].status_code, 404)
        self.route.public = False
        portal.cache.clear()
        self.assertEqual(self.buses()[0].status_code, 404)

    def test_feed_is_cached_for_a_few_seconds(self):
        self.report(self.bus, 3)
        first = self.buses()[1]
        self.bus._apply_position(traccar_position(
            5, self.now.strftime('%Y-%m-%dT%H:%M:%SZ'), -33.470, -70.640, speed_knots=10.0))
        self.assertEqual(self.buses()[1], first)           # still the cached answer
        portal.cache.clear()
        self.assertNotEqual(self.buses()[1], first)

    def test_feed_is_rate_limited_per_address(self):
        statuses = [self.buses()[0].status_code for _ in range(portal.RATE_LIMIT + 1)]
        self.assertEqual(statuses[:portal.RATE_LIMIT], [200] * portal.RATE_LIMIT)
        self.assertEqual(statuses[-1], 429)

    def test_rate_limiter_forgets_old_hits(self):
        limiter = portal.RateLimiter(2, 10.0)
        self.assertTrue(limiter.allow('ip', now=0))
        self.assertTrue(limiter.allow('ip', now=1))
        self.assertFalse(limiter.allow('ip', now=2))
        self.assertTrue(limiter.allow('other', now=2))
        self.assertTrue(limiter.allow('ip', now=12))

    # -- language ----------------------------------------------------------------------
    def test_language_follows_the_browser_then_the_choice(self):
        self.assertIn('Elige tu ruta', self.url_open('/rutas').text)
        english = self.url_open('/rutas', headers={'Accept-Language': 'en-US,en;q=0.9'}).text
        self.assertIn('Pick your route', english)
        unknown = self.url_open('/rutas', headers={'Accept-Language': 'fr'}).text
        self.assertIn('Elige tu ruta', unknown)

    def test_choosing_a_language_is_remembered(self):
        resp = self.url_open('/rutas?lang=en')
        self.assertIn('Pick your route', resp.text)
        self.assertEqual(resp.cookies['bus_lang'], 'en')
        again = self.url_open('/rutas', headers={'Cookie': 'bus_lang=en'})
        self.assertIn('Pick your route', again.text)
        self.opener.cookies.clear()                        # forget the remembered choice
        ignored = self.url_open('/rutas?lang=zz')
        self.assertIn('Elige tu ruta', ignored.text)       # unknown code is ignored
        self.assertNotIn('bus_lang', ignored.cookies)

    def test_script_only_gets_its_own_strings(self):
        html = self.url_open('/rutas/L1?lang=en').text
        self.assertIn('data-i18n', html)
        self.assertIn('no signal', html)

    def test_every_language_has_the_same_keys(self):
        base = set(STRINGS['es'])
        for code, strings in STRINGS.items():
            self.assertEqual(set(strings), base, code)
        for key in portal.JS_STRINGS:
            self.assertIn(key, base)

    def test_public_assets_are_versioned_so_browsers_never_keep_stale_copies(self):
        for url in ('/rutas', '/rutas/L1', '/'):
            html = self.url_open(url).text
            self.assertRegex(html, r'landing\.css\?v=\d+', url)
        self.assertRegex(self.url_open('/rutas/L1').text, r'portal_map\.js\?v=\d+')

    def test_no_invented_numbers_when_no_bus_reports(self):
        html = self.url_open('/rutas').text
        self.assertIn('Ahora no hay buses con señal', html)
        for invented in ('8 buses', 'Frecuencia', 'min</span>', 'Accesible'):
            self.assertNotIn(invented, html)

    def test_route_page_promises_no_arrival_times(self):
        html = self.url_open('/rutas/L1').text
        self.assertNotIn('Llega en', html)
        self.assertNotIn('probabil', html)

    def test_routes_can_be_searched_by_stop_without_accents(self):
        self.env['bus.route.stop'].create({'route_id': self.route.id, 'name': 'Píllaro centro',
                                           'latitude': -1.17, 'longitude': -78.54})
        found = self.url_open('/rutas?q=pillaro').text
        self.assertIn('Linea Centro', found)
        self.assertNotIn('Linea Centro', self.url_open('/rutas?q=quito').text)

    def test_contact_is_only_shown_when_configured(self):
        self.assertNotIn('tel:', self.url_open('/').text)
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.contact_phone', '+593 3 299 9999')
        self.assertIn('tel:+59332999999', self.url_open('/').text)

    def test_landing_sends_passengers_to_the_routes(self):
        self.assertIn('href="/rutas"', self.url_open('/').text)
