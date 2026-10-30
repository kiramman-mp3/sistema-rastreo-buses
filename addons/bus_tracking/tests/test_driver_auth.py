import json
from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from ..controllers.driver_api import login_limiter

LOGIN = '/bus_tracking/driver/login'
ME = '/bus_tracking/driver/me'
LOGOUT = '/bus_tracking/driver/logout'


def make_driver(env, login='chofer1', password='clave-segura-1', groups='bus_tracking.group_bus_driver'):
    return env['res.users'].with_context(no_reset_password=True).create({
        'name': 'Chofer Uno',
        'login': login,
        'password': password,
        'groups_id': [(6, 0, [env.ref(groups).id])],
    })


@tagged('post_install', '-at_install')
class TestDriverToken(TransactionCase):

    def setUp(self):
        super().setUp()
        self.driver = make_driver(self.env)
        self.tokens = self.env['bus.driver.token']

    def test_token_resolves_to_its_driver_and_is_stored_hashed(self):
        raw = self.tokens._issue(self.driver, 'Tablet 1')
        self.assertEqual(self.tokens._user_for(raw), self.driver)
        self.assertNotEqual(self.tokens.search([]).token_hash, raw)

    def test_unknown_or_empty_token_gives_no_user(self):
        self.assertFalse(self.tokens._user_for('nope'))
        self.assertFalse(self.tokens._user_for(''))

    def test_expired_token_is_rejected_and_purged(self):
        raw = self.tokens._issue(self.driver)
        self.tokens.search([]).expires = fields.Datetime.now() - timedelta(seconds=1)
        self.assertFalse(self.tokens._user_for(raw))
        self.tokens._cron_purge()
        self.assertFalse(self.tokens.search([]))

    def test_revoked_token_is_rejected(self):
        raw = self.tokens._issue(self.driver)
        self.tokens._revoke(raw)
        self.assertFalse(self.tokens._user_for(raw))

    def test_token_stops_working_when_user_loses_the_driver_role(self):
        raw = self.tokens._issue(self.driver)
        self.driver.groups_id = [(3, self.env.ref('bus_tracking.group_bus_driver').id)]
        self.assertFalse(self.tokens._user_for(raw))

    def test_token_stops_working_when_user_is_archived(self):
        raw = self.tokens._issue(self.driver)
        self.driver.active = False
        self.assertFalse(self.tokens._user_for(raw))


@tagged('post_install', '-at_install')
class TestBusShift(TransactionCase):

    def setUp(self):
        super().setUp()
        self.route = self.env['bus.route'].create({'name': 'R', 'code': 'R1'})
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus 1'})
        self.bus2 = self.env['bus.vehicle'].create({'name': 'Bus 2'})
        self.driver = make_driver(self.env)
        self.other = make_driver(self.env, login='chofer2')

    def shift(self, user, bus, state='active'):
        return self.env['bus.shift'].create({
            'user_id': user.id, 'vehicle_id': bus.id, 'route_id': self.route.id, 'state': state})

    @mute_logger('odoo.sql_db')
    def test_a_driver_has_one_active_shift(self):
        self.shift(self.driver, self.bus)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.shift(self.driver, self.bus2)

    @mute_logger('odoo.sql_db')
    def test_a_bus_has_one_active_shift(self):
        self.shift(self.driver, self.bus)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.shift(self.other, self.bus)

    def test_finished_shifts_do_not_block_new_ones(self):
        self.shift(self.driver, self.bus, state='done')
        self.shift(self.driver, self.bus, state='done')
        self.shift(self.driver, self.bus)

    def test_driver_reads_only_their_own_shifts(self):
        mine, theirs = self.shift(self.driver, self.bus), self.shift(self.other, self.bus2)
        seen = self.env['bus.shift'].with_user(self.driver).search([])
        self.assertEqual(seen, mine)
        self.assertNotIn(theirs, seen)

    def test_driver_cannot_write_shifts_or_read_tokens(self):
        shift = self.shift(self.driver, self.bus)
        with self.assertRaises(Exception):
            shift.with_user(self.driver).write({'state': 'done'})
        with self.assertRaises(Exception):
            self.env['bus.driver.token'].with_user(self.driver).search([])


@tagged('post_install', '-at_install')
class TestDriverApi(HttpCase):

    def setUp(self):
        super().setUp()
        login_limiter.reset()
        self.driver = make_driver(self.env)
        make_driver(self.env, login='gerente', password='clave-gerente-1', groups='bus_tracking.group_bus_manager')
        self.route = self.env['bus.route'].create({'name': 'Linea Centro', 'code': 'L1'})
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus 1', 'plate': 'ABC-123', 'route_id': self.route.id})

    def post(self, url, data=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        return self.url_open(url, data=json.dumps(data if data is not None else {}), headers=headers)

    def login(self, login='chofer1', password='clave-segura-1'):
        return self.post(LOGIN, {'login': login, 'password': password, 'device': 'Tablet 1'})

    def test_login_returns_a_token_for_a_driver(self):
        resp = self.login()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['driver']['name'], 'Chofer Uno')
        self.assertTrue(resp.json()['token'])

    def test_login_rejects_wrong_password_and_unknown_user_the_same_way(self):
        wrong = self.login(password='mal')
        unknown = self.login(login='nadie')
        self.assertEqual((wrong.status_code, unknown.status_code), (401, 401))
        self.assertEqual(wrong.json(), unknown.json())

    def test_login_rejects_users_without_the_driver_role(self):
        resp = self.login(login='gerente', password='clave-gerente-1')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), {'error': 'invalid_credentials'})

    def test_login_rejects_malformed_bodies(self):
        for body in ({}, {'login': 'chofer1'}, {'login': 1, 'password': 2}, {'login': '', 'password': ''}):
            self.assertEqual(self.post(LOGIN, body).status_code, 400, body)
        raw = self.url_open(LOGIN, data='not json', headers={'Content-Type': 'application/json'})
        self.assertEqual(raw.status_code, 400)

    def test_login_is_rate_limited(self):
        for _ in range(10):
            self.assertEqual(self.login(password='mal').status_code, 401)
        self.assertEqual(self.login(password='mal').status_code, 429)

    def test_login_rejects_get(self):
        self.assertEqual(self.url_open(LOGIN).status_code, 405)

    def test_me_needs_a_valid_token(self):
        self.assertEqual(self.post(ME).status_code, 401)
        self.assertEqual(self.post(ME, token='nope').status_code, 401)

    def test_me_lists_buses_routes_and_no_active_shift(self):
        token = self.login().json()['token']
        data = self.post(ME, token=token).json()
        self.assertEqual(data['driver']['name'], 'Chofer Uno')
        self.assertEqual([b['name'] for b in data['vehicles']], ['Bus 1'])
        self.assertTrue(data['vehicles'][0]['available'])
        self.assertEqual([r['code'] for r in data['routes']], ['L1'])
        self.assertIsNone(data['shift'])

    def test_me_never_exposes_the_gps_identifier(self):
        self.bus.write({'traccar_device_id': 5, 'traccar_unique_id': 'b-secret'})
        token = self.login().json()['token']
        self.assertNotIn('b-secret', self.post(ME, token=token).text)

    def test_me_marks_a_bus_taken_by_someone_else_as_unavailable(self):
        other = make_driver(self.env, login='chofer2')
        self.env['bus.shift'].create({'user_id': other.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id})
        token = self.login().json()['token']
        data = self.post(ME, token=token).json()
        self.assertFalse(data['vehicles'][0]['available'])
        self.assertIsNone(data['shift'])

    def test_logout_revokes_the_token(self):
        token = self.login().json()['token']
        self.assertEqual(self.post(ME, token=token).status_code, 200)
        self.assertEqual(self.post(LOGOUT, token=token).status_code, 200)
        self.assertEqual(self.post(ME, token=token).status_code, 401)
