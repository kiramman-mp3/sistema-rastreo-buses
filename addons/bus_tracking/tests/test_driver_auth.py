import datetime
import json
from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from ..controllers.driver_api import ACCOUNT_LIMIT, LOGIN_LIMIT, account_limiter, login_limiter

LOGIN = '/bus_tracking/driver/login'
ME = '/bus_tracking/driver/me'
LOGOUT = '/bus_tracking/driver/logout'


def make_driver(env, login='chofer1', password='clave-segura-1', groups='bus_tracking.group_bus_driver'):
    # Drivers are portal users, as the Drivers menu creates them; staff are internal users.
    user_type = 'base.group_portal' if groups == 'bus_tracking.group_bus_driver' else 'base.group_user'
    return env['res.users'].with_context(no_reset_password=True).create({
        'name': 'Chofer Uno',
        'login': login,
        'password': password,
        'groups_id': [(6, 0, [env.ref(user_type).id, env.ref(groups).id])],
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
        account_limiter.reset()
        # HttpCase tests share 127.0.0.1. Failed logins in one test would otherwise
        # trip Odoo's cooldown and 401 the later successful-login tests.
        self.env['ir.config_parameter'].sudo().set_param('base.login_cooldown_after', '0')
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
        for _ in range(LOGIN_LIMIT):
            self.assertEqual(self.login(password='mal').status_code, 401)
        self.assertEqual(self.login(password='mal').status_code, 429)

    def test_failures_from_another_address_do_not_lock_the_driver_out(self):
        for _ in range(LOGIN_LIMIT):
            self.login(password='mal')
        login_limiter.reset()                          # the driver's tablet: another address
        self.assertEqual(self.login().status_code, 200)

    def test_one_login_has_a_ceiling_across_addresses(self):
        for attempt in range(ACCOUNT_LIMIT):
            if attempt % LOGIN_LIMIT == 0:
                login_limiter.reset()                  # a new address every ten attempts
            self.assertEqual(self.login(password='mal').status_code, 401)
        login_limiter.reset()
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


@tagged('post_install', '-at_install')
class TestPanelSignIn(TransactionCase):
    """Sign-in to the Odoo panel: longer waits after repeated failures, and a second factor available."""

    def wait(self, failures, seconds_ago):
        previous = datetime.datetime.now() - timedelta(seconds=seconds_ago)
        return self.env['res.users']._on_login_cooldown(failures, previous)

    def test_the_wait_doubles_with_every_failure(self):
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('base.login_cooldown_after', '5')
        icp.set_param('base.login_cooldown_duration', '60')
        self.assertFalse(self.wait(4, 0))              # below the threshold
        self.assertTrue(self.wait(5, 59))
        self.assertFalse(self.wait(5, 61))
        self.assertTrue(self.wait(7, 239))             # 60 s x 4
        self.assertFalse(self.wait(7, 241))
        self.assertTrue(self.wait(50, 3599))           # capped at an hour
        self.assertFalse(self.wait(50, 3601))

    def test_zero_turns_the_wait_off(self):
        self.env['ir.config_parameter'].sudo().set_param('base.login_cooldown_after', '0')
        self.assertFalse(self.wait(100, 0))

    def test_users_can_turn_on_a_second_factor(self):
        totp = self.env['ir.module.module'].search([('name', '=', 'auth_totp')])
        self.assertEqual(totp.state, 'installed')
        self.assertIn('totp_enabled', self.env['res.users']._fields)


@tagged('post_install', '-at_install')
class TestDriverUpcomingTrips(HttpCase):
    """The tablet reminds the driver of their next trips: /driver/me lists them."""

    post = TestDriverApi.post
    login = TestDriverApi.login

    def setUp(self):
        super().setUp()
        login_limiter.reset()
        account_limiter.reset()
        self.env['ir.config_parameter'].sudo().set_param('base.login_cooldown_after', '0')
        self.driver = make_driver(self.env)
        self.route = self.env['bus.route'].create({'name': 'Linea Centro', 'code': 'L1'})
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus 1', 'plate': 'ABC-123', 'route_id': self.route.id})
        for sequence, (name, minutes) in enumerate((('Terminal', 0), ('Hospital', 20))):
            self.env['bus.route.stop'].create({'route_id': self.route.id, 'name': name, 'sequence': sequence,
                                               'latitude': -1.24 - sequence / 100, 'longitude': -78.62,
                                               'planned_offset_min': minutes})

    def trip(self, minutes, driver=None, **extra):
        return self.env['bus.trip'].create(dict({
            'vehicle_id': self.bus.id, 'route_id': self.route.id,
            'planned_start': fields.Datetime.now() + timedelta(minutes=minutes),
            'driver_user_id': (driver or self.driver).id}, **extra))

    def upcoming(self):
        token = self.login().json()['token']
        return self.post(ME, token=token).json()['upcoming']

    def test_the_driver_gets_their_next_trips_soonest_first(self):
        later, sooner = self.trip(180), self.trip(30)
        trips = self.upcoming()
        self.assertEqual([t['id'] for t in trips], [sooner.id, later.id])
        self.assertEqual((trips[0]['route_code'], trips[0]['vehicle_name']), ('L1', 'Bus 1'))
        self.assertTrue(trips[0]['planned_start'].endswith('Z'))

    def test_only_their_planned_trips_of_the_next_day(self):
        other = make_driver(self.env, login='chofer2', password='clave-segura-2')
        self.trip(30, driver=other)
        self.trip(-30)                                       # already due
        self.trip(60 * 25)                                   # beyond the next 24 hours
        self.trip(90).action_cancel()
        self.assertEqual(self.upcoming(), [])

    def test_a_schedule_gives_its_driver_to_the_trips_it_creates(self):
        schedule = self.env['bus.route.schedule'].create({
            'route_id': self.route.id, 'departure_time': 7.5, 'vehicle_id': self.bus.id,
            'driver_user_id': self.driver.id, 'saturday': True, 'sunday': True})
        today = fields.Date.today()
        trips = schedule._generate_trips(today, today + timedelta(days=1))
        self.assertTrue(trips)
        self.assertEqual(trips.driver_user_id, self.driver)
