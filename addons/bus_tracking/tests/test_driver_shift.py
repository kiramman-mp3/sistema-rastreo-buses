import json
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, tagged

from ..controllers.driver_api import login_limiter
from .test_driver_auth import make_driver

LOGIN = '/bus_tracking/driver/login'
ME = '/bus_tracking/driver/me'
START = '/bus_tracking/driver/shift/start'
END = '/bus_tracking/driver/shift/end'
STATE = '/bus_tracking/driver/state'
ROUTE = '/bus_tracking/driver/route'
INCIDENT = '/bus_tracking/driver/incident'


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
class TestDriverShiftApi(HttpCase):

    def setUp(self):
        super().setUp()
        login_limiter.reset()
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

    def test_a_driver_does_not_see_another_driver_shift_in_me(self):
        self.start(self.token('chofer2'))
        data = self.post(ME, token=self.token()).json()
        self.assertIsNone(data['shift'])
        self.assertFalse(data['vehicles'][0]['available'])
