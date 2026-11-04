import json
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, tagged

from ..controllers.driver_api import error_limiter, login_limiter
from ..models.utils import pick_odoo_lang
from .test_driver_auth import make_driver

LOGIN = '/bus_tracking/driver/login'
ME = '/bus_tracking/driver/me'
START = '/bus_tracking/driver/shift/start'
END = '/bus_tracking/driver/shift/end'
STATE = '/bus_tracking/driver/state'
ROUTE = '/bus_tracking/driver/route'
INCIDENT = '/bus_tracking/driver/incident'
CLIENT_ERROR = '/bus_tracking/driver/client_error'


@tagged('post_install', '-at_install')
class TestShiftCron(TransactionCase):

    def setUp(self):
        super().setUp()
        self.route = self.env['bus.route'].create({'name': 'R', 'code': 'R1'})
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus 1', 'route_id': self.route.id})
        self.driver = make_driver(self.env)

    def test_stale_active_shifts_are_closed_and_the_driver_cleared(self):
        shift = self.env['bus.shift'].create({
            'user_id': self.driver.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id})
        shift._assign_vehicle()
        self.assertEqual(self.bus.driver_id, self.driver.partner_id)
        shift.start = fields.Datetime.now() - timedelta(hours=15)
        self.env['bus.shift']._cron_close_stale()
        self.assertEqual(shift.state, 'done')
        self.assertTrue(shift.end)
        self.assertFalse(self.bus.driver_id)

    def test_a_fresh_shift_is_left_open(self):
        shift = self.env['bus.shift'].create({
            'user_id': self.driver.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id})
        self.env['bus.shift']._cron_close_stale()
        self.assertEqual(shift.state, 'active')


@tagged('post_install', '-at_install')
class TestOdooLanguagePick(TransactionCase):
    """The app language (es, en, qu) is mapped to an Odoo language that is installed."""

    def test_the_best_installed_spanish_wins(self):
        self.assertEqual(pick_odoo_lang('es', ['en_US', 'es_ES', 'es_EC']), 'es_EC')
        self.assertEqual(pick_odoo_lang('es', ['en_US', 'es_ES']), 'es_ES')

    def test_any_other_spanish_is_better_than_none(self):
        self.assertEqual(pick_odoo_lang('es', ['en_US', 'es_AR', 'es_MX']), 'es_AR')

    def test_english_and_kichwa(self):
        self.assertEqual(pick_odoo_lang('en', ['es_EC', 'en_US']), 'en_US')
        self.assertEqual(pick_odoo_lang('qu', ['en_US', 'es_EC', 'qu_EC']), 'qu_EC')
        # where Kichwa is not installed the driver reads Spanish
        self.assertEqual(pick_odoo_lang('qu', ['en_US', 'es_EC']), 'es_EC')

    def test_nothing_installed_or_nonsense_falls_back(self):
        self.assertEqual(pick_odoo_lang('es', ['en_US'], fallback='en_US'), 'en_US')
        self.assertIsNone(pick_odoo_lang('es', []))
        for junk in (None, 'zz', 42, ['es'], {'es': 1}, ''):
            self.assertEqual(pick_odoo_lang(junk, ['es_EC'], fallback='x'), 'x')

    def new_driver(self, login, **vals):
        return self.env['res.users'].with_context(no_reset_password=True).create(dict({
            'name': 'Chofer Nuevo', 'login': login, 'password': 'clave-segura-1', 'is_bus_driver': True}, **vals))

    def test_a_new_driver_reads_spanish_when_it_is_installed(self):
        self.env['res.lang']._activate_lang('es_EC')
        self.assertEqual(self.new_driver('chofer-es').lang, 'es_EC')

    def test_a_language_chosen_for_the_driver_is_kept(self):
        self.env['res.lang']._activate_lang('es_EC')
        self.assertEqual(self.new_driver('chofer-en', lang='en_US').lang, 'en_US')

    def test_without_spanish_installed_the_driver_gets_the_default(self):
        self.assertEqual(self.new_driver('chofer-def').lang, self.env.user.lang or 'en_US')


@tagged('post_install', '-at_install')
class TestTripProgress(TransactionCase):

    def setUp(self):
        super().setUp()
        self.route = self.env['bus.route'].create({'name': 'R', 'code': 'R1', 'stop_ids': [
            (0, 0, {'sequence': i, 'name': name, 'latitude': -1.2 - i / 100, 'longitude': -78.6})
            for i, name in enumerate(['A', 'B', 'C'], start=1)]})
        self.a, self.b, self.c = self.route.stop_ids
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus T', 'route_id': self.route.id})
        self.shift = self.env['bus.shift'].create({
            'user_id': make_driver(self.env).id, 'vehicle_id': self.bus.id, 'route_id': self.route.id})
        self.shift.start = fields.Datetime.now() - timedelta(hours=3)

    def arrive(self, stop, minutes_ago):
        self.env['bus.stop.arrival'].create({
            'vehicle_id': self.bus.id, 'stop_id': stop.id,
            'arrival_time': fields.Datetime.now() - timedelta(minutes=minutes_ago)})

    def test_first_trip_goes_forward(self):
        self.arrive(self.a, 100)
        trip = self.shift._trip_progress()
        self.assertEqual(trip['direction'], 'forward')
        self.assertEqual(trip['next_stop'], self.b)

    def test_after_the_last_stop_the_bus_heads_back(self):
        for stop, ago in ((self.a, 100), (self.b, 90), (self.c, 80)):
            self.arrive(stop, ago)
        trip = self.shift._trip_progress()
        self.assertEqual(trip['direction'], 'back')
        self.assertEqual(list(trip['stops']), [self.c, self.b, self.a])
        self.assertEqual(trip['next_stop'], self.b)
        self.assertEqual(set(trip['arrived']), {self.c.id})

    def test_the_second_lap_has_a_next_stop_again(self):
        for stop, ago in ((self.a, 100), (self.b, 90), (self.c, 80), (self.b, 70), (self.a, 60)):
            self.arrive(stop, ago)
        trip = self.shift._trip_progress()
        self.assertEqual(trip['direction'], 'forward')
        self.assertEqual(trip['next_stop'], self.b)

    def test_arrivals_before_the_shift_do_not_count(self):
        self.arrive(self.c, 300)
        trip = self.shift._trip_progress()
        self.assertEqual(trip['direction'], 'forward')
        self.assertEqual(trip['next_stop'], self.a)


@tagged('post_install', '-at_install')
class TestDriverShiftApi(HttpCase):

    def setUp(self):
        super().setUp()
        login_limiter.reset()
        error_limiter.reset()
        self.env['ir.config_parameter'].sudo().set_param('base.login_cooldown_after', '0')
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.gps_url', 'https://gps.example.com/')
        self.driver = make_driver(self.env)
        self.other = make_driver(self.env, login='chofer2')
        self.route = self.env['bus.route'].create({
            'name': 'Linea Centro',
            'code': 'L1',
            'stop_ids': [
                (0, 0, {'sequence': 10, 'name': 'Terminal', 'latitude': -1.24, 'longitude': -78.62, 'radius': 50}),
                (0, 0, {'sequence': 20, 'name': 'Campus', 'latitude': -1.27, 'longitude': -78.63, 'radius': 40}),
            ],
        })
        self.bus = self.env['bus.vehicle'].create({
            'name': 'Bus 1', 'plate': 'ABC-123', 'route_id': self.route.id,
            'traccar_device_id': 9, 'traccar_unique_id': 'b-secret',
        })
        self.stops = {s.name: s for s in self.route.stop_ids}

    def post(self, url, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        resp = self.url_open(url, data=json.dumps(data if data is not None else {}), headers=headers)
        self.env.invalidate_all()
        return resp

    def token(self, login='chofer1', password='clave-segura-1'):
        return self.post(LOGIN, {'login': login, 'password': password}).json()['token']

    def start(self, token, vehicle=None, route=None):
        return self.post(START, {
            'vehicle_id': (vehicle or self.bus).id,
            'route_id': (route or self.route).id,
        }, token=token)

    def test_start_returns_gps_id_only_there_and_assigns_the_partner(self):
        token = self.token()
        resp = self.start(token)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data['traccar_unique_id'], 'b-secret')
        self.assertEqual(data['gps_url'], 'https://gps.example.com')
        self.assertEqual(data['shift']['vehicle_id'], self.bus.id)
        me = self.post(ME, token=token)
        self.assertNotIn('b-secret', me.text)
        self.assertEqual(me.json()['shift']['id'], data['shift']['id'])
        self.assertEqual(self.bus.driver_id, self.driver.partner_id)
        self.assertEqual(self.bus.route_id, self.route)

    def test_start_rejects_a_bus_without_gps(self):
        self.bus.traccar_unique_id = False
        resp = self.start(self.token())
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json(), {'error': 'no_gps'})

    def test_start_rejects_a_second_shift_for_the_same_driver(self):
        token = self.token()
        self.assertEqual(self.start(token).status_code, 200)
        bus2 = self.env['bus.vehicle'].create({
            'name': 'Bus 2', 'traccar_unique_id': 'other-id', 'route_id': self.route.id})
        resp = self.start(token, vehicle=bus2)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json(), {'error': 'conflict'})

    def test_start_rejects_a_bus_already_on_a_shift(self):
        self.assertEqual(self.start(self.token('chofer2')).status_code, 200)
        resp = self.start(self.token())
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json(), {'error': 'conflict'})

    def test_end_clears_the_driver_and_blocks_state(self):
        token = self.token()
        self.assertEqual(self.start(token).status_code, 200)
        self.assertEqual(self.post(END, token=token).status_code, 200)
        self.assertFalse(self.bus.driver_id)
        self.assertEqual(self.post(STATE, token=token).status_code, 409)
        self.assertIsNone(self.post(ME, token=token).json()['shift'])

    def test_state_and_route_need_an_active_shift(self):
        token = self.token()
        self.assertEqual(self.post(STATE, token=token).json(), {'error': 'no_shift'})
        self.assertEqual(self.post(ROUTE, token=token).status_code, 409)

    def test_state_marks_a_stop_reached_during_the_shift(self):
        token = self.token()
        self.start(token)
        terminal = self.stops['Terminal']
        self.env['bus.stop.arrival'].create({
            'vehicle_id': self.bus.id, 'stop_id': terminal.id, 'arrival_time': fields.Datetime.now()})
        self.bus.current_stop_id = terminal
        data = self.post(STATE, token=token).json()
        by_id = {row['id']: row for row in data['stops']}
        self.assertTrue(by_id[terminal.id]['arrived_at'])
        self.assertIsNone(by_id[self.stops['Campus'].id]['arrived_at'])
        self.assertEqual(data['current_stop_id'], terminal.id)
        self.assertEqual(data['next_stop_id'], self.stops['Campus'].id)

    def test_state_accepts_the_app_language_and_ignores_nonsense(self):
        token = self.token()
        self.start(token)
        for body in ({'lang': 'es'}, {'lang': 'en'}, {'lang': 'qu'}, {'lang': 'zz'}, {'lang': ['es']}, {}):
            resp = self.post(STATE, body, token=token)
            self.assertEqual(resp.status_code, 200, body)
            self.assertIn('alerts', resp.json())

    def test_alert_details_follow_the_language_of_the_app(self):
        """The Odoo user of the driver reads English; the app asks for Spanish, English or Kichwa."""
        self.env['res.lang']._activate_lang('es_EC')
        self.env['ir.module.module'].search([('name', '=', 'bus_tracking')])._update_translations(
            filter_lang='qu_EC', overwrite=True)
        token = self.token()
        self.start(token)
        self.env['bus.alert'].create({
            'vehicle_id': self.bus.id, 'kind': 'off_route', 'start_time': fields.Datetime.now(),
            'distance_m': 400.0, 'threshold': 150.0})
        english = 'Up to 400 m away from its route (limit 150 m)'
        spanish = 'Hasta 400 m fuera de su ruta (límite 150 m)'
        kichwa = 'Ñanmanta 400 m karukama (límite 150 m)'

        def detail(body):
            return self.post(STATE, body, token=token).json()['alerts'][0]['detail']

        self.assertEqual(detail({'lang': 'es'}), spanish)
        self.assertEqual(detail({'lang': 'qu'}), kichwa)
        self.assertEqual(detail({'lang': 'en'}), english)
        self.assertEqual(detail({}), english)               # no language sent: the one of the Odoo user
        self.assertEqual(detail({'lang': 'zz'}), english)   # not an app language: ignored

    def test_client_error_needs_a_driver_session(self):
        self.assertEqual(self.post(CLIENT_ERROR, {'message': 'boom'}).status_code, 401)

    def test_client_error_goes_to_the_log_with_who_and_where(self):
        token = self.token()
        self.start(token)
        with self.assertLogs('odoo.addons.bus_tracking.controllers.driver_api', level='WARNING') as logs:
            resp = self.post(CLIENT_ERROR, {
                'message': 'TypeError: x is undefined', 'stack': 'at a (b.js:1)', 'app': '1.0.0', 'screen': 'shift'},
                token=token)
        self.assertEqual(resp.json(), {'ok': True})
        line = logs.output[0]
        self.assertIn('Tablet error', line)
        self.assertIn('driver=chofer1', line)
        self.assertIn('bus=Bus 1', line)
        self.assertIn('app=1.0.0', line)
        self.assertIn('message=TypeError: x is undefined', line)

    def test_client_error_works_without_a_shift_and_cannot_forge_log_lines(self):
        token = self.token()
        with self.assertLogs('odoo.addons.bus_tracking.controllers.driver_api', level='WARNING') as logs:
            resp = self.post(CLIENT_ERROR, {'message': 'one\n2026-11-02 ERROR fake line\r\nthree'}, token=token)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(logs.output), 1)
        self.assertNotIn('\n', logs.output[0])
        self.assertIn('bus=-', logs.output[0])

    def test_client_error_rejects_bad_input(self):
        token = self.token()
        bad = (
            {}, {'message': ''}, {'message': '   '}, {'message': 123}, {'message': 'x' * 501},
            {'message': 'x', 'stack': 'y' * 3001}, {'message': 'x', 'stack': ['a']},
            {'message': 'x', 'app': 'a' * 61}, {'message': 'x', 'screen': 5})
        for body in bad:
            self.assertEqual(self.post(CLIENT_ERROR, body, token=token).status_code, 400, body)

    def test_client_error_is_rate_limited_per_driver(self):
        token = self.token()
        codes = [self.post(CLIENT_ERROR, {'message': 'loop'}, token=token).status_code for _ in range(22)]
        self.assertEqual(codes[:20], [200] * 20)
        self.assertEqual(codes[20:], [429, 429])

    def test_route_returns_stops_and_the_line_between_them(self):
        token = self.token()
        self.start(token)
        data = self.post(ROUTE, token=token).json()
        self.assertEqual([s['name'] for s in data['stops']], ['Terminal', 'Campus'])
        self.assertEqual(data['stops'][0]['radius'], 50)
        self.assertEqual(len(data['lines'][0]['points']), 2)
        self.assertNotIn('b-secret', json.dumps(data))

    def test_incident_requires_a_shift_and_valid_coordinates(self):
        token = self.token()
        self.assertEqual(self.post(INCIDENT, {'kind': 'traffic'}, token=token).status_code, 409)
        self.start(token)
        self.assertEqual(self.post(INCIDENT, {'kind': 'nope'}, token=token).status_code, 400)
        self.assertEqual(self.post(INCIDENT, {
            'kind': 'accident', 'lat': 95, 'lon': -78.6}, token=token).status_code, 400)
        resp = self.post(INCIDENT, {
            'kind': 'breakdown', 'note': 'Humos', 'lat': -1.24, 'lon': -78.62}, token=token)
        self.assertEqual(resp.status_code, 200, resp.text)
        incident = self.env['bus.incident'].browse(resp.json()['id'])
        self.assertEqual(incident.kind, 'breakdown')
        self.assertEqual(incident.vehicle_id, self.bus)
        self.assertEqual(incident.user_id, self.driver)

    def test_sos_is_its_own_kind_and_wakes_the_push_cron(self):
        token = self.token()
        self.start(token)
        cron = self.env.ref('bus_tracking.cron_push_incidents')
        before = self.env['ir.cron.trigger'].search_count([('cron_id', '=', cron.id)])
        resp = self.post(INCIDENT, {'kind': 'sos', 'lat': -1.24, 'lon': -78.62}, token=token)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(self.env['bus.incident'].browse(resp.json()['id']).kind, 'sos')
        self.assertGreater(self.env['ir.cron.trigger'].search_count([('cron_id', '=', cron.id)]), before)

    def test_the_tablet_learns_when_the_office_saw_its_sos(self):
        token = self.token()
        self.start(token)
        self.assertIsNone(self.post(STATE, token=token).json()['sos'])
        sos_id = self.post(INCIDENT, {'kind': 'sos'}, token=token).json()['id']
        sos = self.post(STATE, token=token).json()['sos']
        self.assertEqual((sos['id'], sos['seen_at']), (sos_id, None))
        manager = self.env['res.users'].create({
            'name': 'Despacho', 'login': 'despacho',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id,
                                  self.env.ref('bus_tracking.group_bus_user').id])]})
        self.env['bus.incident'].browse(sos_id).with_user(manager).action_acknowledge()
        sos = self.post(STATE, token=token).json()['sos']
        self.assertTrue(sos['seen_at'])
        self.assertEqual(sos['seen_by'], 'Despacho')

    def test_a_driver_does_not_see_another_driver_shift_in_me(self):
        self.start(self.token('chofer2'))
        data = self.post(ME, token=self.token()).json()
        self.assertIsNone(data['shift'])
        self.assertFalse(data['vehicles'][0]['available'])

    def test_start_needs_the_gps_address(self):
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.gps_url', '')
        resp = self.start(self.token())
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json(), {'error': 'no_gps_url'})
        self.assertFalse(self.env['bus.shift'].search_count([('vehicle_id', '=', self.bus.id)]))

    def test_start_refuses_an_archived_route(self):
        self.route.active = False
        self.assertEqual(self.start(self.token()).status_code, 400)

    def test_me_says_which_buses_have_gps(self):
        self.env['bus.vehicle'].create({'name': 'Sin GPS', 'route_id': self.route.id})
        vehicles = {v['name']: v for v in self.post(ME, token=self.token()).json()['vehicles']}
        self.assertTrue(vehicles['Bus 1']['has_gps'])
        self.assertFalse(vehicles['Sin GPS']['has_gps'])

    def test_an_incident_keeps_the_time_it_was_reported(self):
        token = self.token()
        self.assertEqual(self.start(token).status_code, 200)
        shift = self.env['bus.shift'].search([('user_id', '=', self.driver.id), ('state', '=', 'active')])
        shift.start = fields.Datetime.now() - timedelta(hours=1)
        pressed = (fields.Datetime.now() - timedelta(minutes=20)).replace(microsecond=0)
        resp = self.post(INCIDENT, {'kind': 'sos', 'reported_at': pressed.isoformat() + 'Z'}, token=token)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(self.env['bus.incident'].browse(resp.json()['id']).reported_at, pressed)
        # A time before the shift or in the future is replaced by the time it arrived.
        for wrong in ('2001-01-01T00:00:00Z', '2999-01-01T00:00:00Z', 'ayer'):
            incident = self.env['bus.incident'].browse(
                self.post(INCIDENT, {'kind': 'traffic', 'reported_at': wrong}, token=token).json()['id'])
            self.assertGreater(incident.reported_at, pressed)
