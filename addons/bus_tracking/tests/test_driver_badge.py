import json
from datetime import timedelta

from odoo import fields
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
        uid = self.env['res.users'].authenticate(
            self.env.cr.dbname, 'chofer_pwd', 'mi-clave-secreta', {'interactive': False})
        self.assertEqual(uid, new_driver.id)

        new_driver.write({'driver_password': 'otra-clave-nueva'})
        uid_new = self.env['res.users'].authenticate(
            self.env.cr.dbname, 'chofer_pwd', 'otra-clave-nueva', {'interactive': False})
        self.assertEqual(uid_new, new_driver.id)



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
