import json
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessDenied, AccessError
from odoo.tests import HttpCase, TransactionCase, tagged

from ..controllers.driver_api import login_limiter
from .test_driver_auth import make_driver


@tagged('post_install', '-at_install')
class TestDriverBadge(TransactionCase):

    def setUp(self):
        super().setUp()
        self.driver = make_driver(self.env, login='chofer_badge')
        self.tokens = self.env['bus.driver.token']

    def test_issue_badge_creates_badge_token_and_replaces_old(self):
        raw1 = self.tokens._issue_badge(self.driver)
        self.assertTrue(raw1)
        self.assertEqual(self.tokens._user_for_badge(raw1), self.driver)

        # Generating a second badge invalidates the first
        raw2 = self.tokens._issue_badge(self.driver)
        self.assertTrue(raw2)
        self.assertFalse(self.tokens._user_for_badge(raw1))
        self.assertEqual(self.tokens._user_for_badge(raw2), self.driver)

    def test_revoke_badge_invalidates_badge_token(self):
        raw = self.tokens._issue_badge(self.driver)
        self.assertEqual(self.tokens._user_for_badge(raw), self.driver)
        self.tokens._revoke_badge(self.driver)
        self.assertFalse(self.tokens._user_for_badge(raw))

    def test_badge_actions_on_res_users(self):
        self.assertFalse(self.driver.driver_badge_active)
        self.driver.action_generate_driver_badge()
        self.assertTrue(self.driver.driver_badge_active)
        self.assertTrue(self.driver.driver_badge_qr)
        self.assertTrue(self.driver.driver_badge_link.startswith('uta-buses://login?'))

        self.driver.action_revoke_driver_badge()
        self.assertFalse(self.driver.driver_badge_active)
        self.assertFalse(self.driver.driver_badge_qr)

    def test_is_bus_driver_search_and_compute(self):
        self.assertTrue(self.driver.is_bus_driver)
        drivers = self.env['res.users'].search([('is_bus_driver', '=', True)])
        self.assertIn(self.driver, drivers)

    def test_driver_password_set_on_create_and_write(self):
        new_driver = self.env['res.users'].create({
            'name': 'Chofer Con Password',
            'login': 'chofer_pwd',
            'is_bus_driver': True,
            'driver_password': 'mi-clave-secreta',
        })
        self.assertTrue(new_driver.is_bus_driver)
        # authenticate() opens its own cursor and cannot see this test's uncommitted user,
        # so the password is checked directly.
        new_driver.with_user(new_driver)._check_credentials('mi-clave-secreta', {'interactive': False})

        new_driver.write({'driver_password': 'otra-clave-nueva'})
        new_driver.with_user(new_driver)._check_credentials('otra-clave-nueva', {'interactive': False})
        with self.assertRaises(AccessDenied):
            new_driver.with_user(new_driver)._check_credentials('mi-clave-secreta', {'interactive': False})

    def test_drivers_from_the_menu_are_portal_users(self):
        driver = self.env['res.users'].with_context(default_is_bus_driver=True).create({
            'name': 'Chofer Portal', 'login': 'chofer_portal'})
        self.assertTrue(driver.share)
        self.assertTrue(driver.has_group('base.group_portal'))
        self.assertFalse(driver.has_group('base.group_user'))
        self.assertTrue(driver.is_bus_driver)

    def test_only_managers_issue_or_revoke_badges(self):
        viewer = make_driver(self.env, login='visor_badge', groups='bus_tracking.group_bus_user')
        other = make_driver(self.env, login='chofer_otro')
        for intruder in (viewer, other):
            with self.assertRaises(AccessError):
                self.driver.with_user(intruder).action_generate_driver_badge()
        self.driver.action_generate_driver_badge()
        for intruder in (viewer, other):
            with self.assertRaises(AccessError):
                self.driver.with_user(intruder).action_revoke_driver_badge()
        self.assertTrue(self.driver.driver_badge_active)

        manager = make_driver(self.env, login='gestor_badge', groups='bus_tracking.group_bus_manager')
        self.driver.with_user(manager).action_revoke_driver_badge()
        self.assertFalse(self.driver.driver_badge_active)

    def test_only_managers_read_the_badge_link(self):
        self.driver.action_generate_driver_badge()
        viewer = make_driver(self.env, login='visor_link', groups='bus_tracking.group_bus_user')
        with self.assertRaises(AccessError):
            self.driver.with_user(viewer).read(['driver_badge_link'])
        with self.assertRaises(AccessError):
            self.driver.with_user(viewer).read(['driver_badge_qr'])
        manager = make_driver(self.env, login='gestor_link', groups='bus_tracking.group_bus_manager')
        link = self.driver.with_user(manager).read(['driver_badge_link'])[0]['driver_badge_link']
        self.assertTrue(link.startswith('uta-buses://login?'))

    def test_a_badge_is_not_a_session(self):
        raw = self.tokens._issue_badge(self.driver)
        self.assertFalse(self.tokens._user_for(raw))
        # Signing out with the badge as bearer does not revoke it.
        self.tokens._revoke(raw)
        self.assertEqual(self.tokens._user_for_badge(raw), self.driver)

    def test_a_session_never_passes_for_a_badge(self):
        raw = self.tokens._issue(self.driver, 'badge_qr')
        self.assertFalse(self.tokens._user_for_badge(raw))
        self.assertEqual(self.tokens._user_for(raw), self.driver)

    def test_signing_the_tablet_out_keeps_the_badge(self):
        badge = self.tokens._issue_badge(self.driver)
        session = self.tokens._issue(self.driver, 'Tablet 1')
        self.tokens._revoke_sessions(self.driver)
        self.assertFalse(self.tokens._user_for(session))
        self.assertEqual(self.tokens._user_for_badge(badge), self.driver)



@tagged('post_install', '-at_install')
class TestDriverBadgeApi(HttpCase):

    def setUp(self):
        super().setUp()
        login_limiter.reset()
        self.env['ir.config_parameter'].sudo().set_param('base.login_cooldown_after', '0')
        self.driver = make_driver(self.env, login='chofer_qr_api')
        self.tokens = self.env['bus.driver.token']

    def test_login_badge_exchanges_token_for_session(self):
        raw_badge = self.tokens._issue_badge(self.driver)
        resp = self.url_open(
            '/bus_tracking/driver/login_badge',
            data=json.dumps({'badge_token': raw_badge, 'device': 'Tablet A'}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('token', data)
        self.assertEqual(data['driver']['name'], self.driver.name)

        session_token = data['token']
        # The badge token remains valid after exchanging
        self.assertEqual(self.tokens._user_for_badge(raw_badge), self.driver)
        # The session token also works for standard driver endpoints
        self.assertEqual(self.tokens._user_for(session_token), self.driver)

    def test_login_badge_rejects_invalid_token(self):
        resp = self.url_open(
            '/bus_tracking/driver/login_badge',
            data=json.dumps({'badge_token': 'non-existent-token'}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 401)

    def _post(self, url, body, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer %s' % token
        return self.url_open(url, data=json.dumps(body), headers=headers)

    def test_login_badge_rejects_a_session_token(self):
        session = self.tokens._issue(self.driver, 'Tablet A')
        resp = self._post('/bus_tracking/driver/login_badge', {'badge_token': session})
        self.assertEqual(resp.status_code, 401)

    def test_a_badge_does_not_open_the_driver_api(self):
        badge = self.tokens._issue_badge(self.driver)
        self.assertEqual(self._post('/bus_tracking/driver/me', {}, badge).status_code, 401)

    def test_logout_keeps_the_badge(self):
        badge = self.tokens._issue_badge(self.driver)
        session = self._post('/bus_tracking/driver/login_badge', {'badge_token': badge}).json()['token']
        self.assertEqual(self._post('/bus_tracking/driver/logout', {}, session).status_code, 200)
        self.assertFalse(self.tokens._user_for(session))
        self.assertEqual(self.tokens._user_for_badge(badge), self.driver)
