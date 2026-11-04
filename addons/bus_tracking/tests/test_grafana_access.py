import base64
import hashlib
import hmac
import json
import time
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged

from ..models.bus_grafana import DASHBOARDS, ISSUER, MIN_SECRET, sign

SECRET = 'a-long-shared-secret-for-tests'


def decode(token, secret=SECRET):
    """Checks the signature the way Grafana does and returns (header, claims)."""
    head, body, signature = token.split('.')
    expected = hmac.new(secret.encode(), ('%s.%s' % (head, body)).encode(), hashlib.sha256).digest()
    assert hmac.compare_digest(base64.urlsafe_b64decode(signature + '=='), expected), 'bad signature'
    return (json.loads(base64.urlsafe_b64decode(head + '==')), json.loads(base64.urlsafe_b64decode(body + '==')))


@tagged('post_install', '-at_install')
class TestGrafanaAccess(TransactionCase):

    def setUp(self):
        super().setUp()
        self.params = self.env['ir.config_parameter'].sudo()
        self.params.set_param('bus_tracking.grafana_url', 'https://grafana.example.com/')
        self.params.set_param('bus_tracking.grafana_jwt_secret', SECRET)
        self.params.set_param('bus_tracking.grafana_token_minutes', '')
        self.user = self.env['res.users'].create({
            'name': 'Lector de buses', 'login': 'graf-user', 'email': 'lector@example.com',
            'groups_id': [(6, 0, [self.env.ref('bus_tracking.group_bus_user').id])]})
        self.access = self.env['bus.grafana'].with_user(self.user).access

    def test_a_bus_user_gets_the_address_and_a_signed_token(self):
        result = self.access()
        self.assertTrue(result['configured'])
        self.assertEqual(result['url'], 'https://grafana.example.com')
        header, claims = decode(result['token'])
        self.assertEqual((header['alg'], header['kid']), ('HS256', 'odoo'))
        self.assertEqual(claims['iss'], ISSUER)
        self.assertEqual(claims['role'], 'Viewer')

    def test_the_token_says_who_it_is_for_without_a_name(self):
        result = self.access()
        _header, claims = decode(result['token'])
        self.assertEqual(claims['sub'], 'odoo-%s' % self.user.id)
        text = json.dumps(claims)
        for private in (self.user.login, self.user.name, self.user.email):
            self.assertNotIn(private, text)

    def test_the_role_is_always_viewer_even_for_a_manager(self):
        manager = self.env['res.users'].create({
            'name': 'Gestor', 'login': 'graf-manager',
            'groups_id': [(6, 0, [self.env.ref('bus_tracking.group_bus_manager').id])]})
        result = self.env['bus.grafana'].with_user(manager).access()
        self.assertTrue(result['can_manage'])
        self.assertEqual(decode(result['token'])[1]['role'], 'Viewer')
        self.assertFalse(self.access()['can_manage'])

    def test_it_lasts_one_working_day_unless_set_otherwise(self):
        result = self.access()
        _header, claims = decode(result['token'])
        self.assertEqual(result['expires_in'], 480 * 60)
        self.assertEqual(claims['exp'] - claims['iat'], 480 * 60)
        self.assertAlmostEqual(claims['iat'], time.time(), delta=5)

    def test_the_length_can_be_set_and_is_kept_between_5_minutes_and_a_day(self):
        for value, minutes in (('30', 30), ('1', 5), ('99999', 1440), ('abc', 480)):
            self.params.set_param('bus_tracking.grafana_token_minutes', value)
            self.assertEqual(self.access()['expires_in'], minutes * 60, value)

    def test_the_token_stops_working_when_it_expires(self):
        self.params.set_param('bus_tracking.grafana_token_minutes', '5')
        _header, claims = decode(self.access()['token'])
        self.assertGreater(claims['exp'], time.time())
        self.assertLess(claims['exp'], time.time() + 6 * 60)
        self.assertLessEqual(claims['nbf'], claims['iat'])

    def test_a_token_signed_with_another_secret_does_not_verify(self):
        with self.assertRaises(AssertionError):
            decode(self.access()['token'], secret='not-the-shared-secret')
        with self.assertRaises(AssertionError):
            decode(sign({'sub': 'x'}, 'someone-elses-secret-key'))

    def test_the_secret_never_travels(self):
        self.assertNotIn(SECRET, json.dumps(self.access()))

    def test_it_lists_the_six_dashboards(self):
        result = self.access()
        self.assertEqual([d['uid'] for d in result['dashboards']], [uid for uid, _title in DASHBOARDS])
        self.assertEqual(len(result['dashboards']), 6)

    def test_without_address_or_secret_it_says_it_is_not_set_up(self):
        for key in ('bus_tracking.grafana_url', 'bus_tracking.grafana_jwt_secret'):
            self.params.set_param(key, '')
            with patch.dict('os.environ', {}, clear=False):
                result = self.access()
            self.assertEqual(result, {'configured': False, 'can_manage': False})
            self.params.set_param('bus_tracking.grafana_url', 'https://grafana.example.com')
            self.params.set_param('bus_tracking.grafana_jwt_secret', SECRET)

    def test_a_short_secret_is_refused(self):
        self.params.set_param('bus_tracking.grafana_jwt_secret', 'x' * (MIN_SECRET - 1))
        self.assertFalse(self.access()['configured'])

    def test_the_environment_is_used_when_nothing_is_set(self):
        self.params.set_param('bus_tracking.grafana_url', '')
        self.params.set_param('bus_tracking.grafana_jwt_secret', '')
        env = {'GRAFANA_URL': 'https://graf.example.org', 'GRAFANA_JWT_SECRET': 'secret-from-the-environment'}
        with patch.dict('os.environ', env):
            result = self.access()
        self.assertEqual(result['url'], 'https://graf.example.org')
        decode(result['token'], secret='secret-from-the-environment')

    def test_what_is_set_in_odoo_wins_over_the_environment(self):
        with patch.dict('os.environ', {'GRAFANA_URL': 'https://other.example.org', 'GRAFANA_JWT_SECRET': 'y' * 20}):
            result = self.access()
        self.assertEqual(result['url'], 'https://grafana.example.com')
        decode(result['token'])

    def test_people_outside_the_bus_groups_get_nothing(self):
        for name, group in (('Interno', 'base.group_user'), ('Chofer', 'base.group_portal')):
            outsider = self.env['res.users'].create({
                'name': name, 'login': 'graf-' + name.lower(), 'groups_id': [(6, 0, [self.env.ref(group).id])]})
            with self.assertRaises(AccessError):
                self.env['bus.grafana'].with_user(outsider).access()


@tagged('post_install', '-at_install')
class TestGrafanaRoute(HttpCase):

    def call(self):
        resp = self.url_open('/bus_tracking/grafana/token', data=json.dumps(
            {'jsonrpc': '2.0', 'method': 'call', 'params': {}}), headers={'Content-Type': 'application/json'})
        return resp.json()

    def setUp(self):
        super().setUp()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('bus_tracking.grafana_url', 'https://grafana.example.com')
        params.set_param('bus_tracking.grafana_jwt_secret', SECRET)

    def test_it_needs_a_session(self):
        self.assertIn('error', self.call())

    def test_a_driver_of_the_portal_is_refused(self):
        self.env['res.users'].create({
            'name': 'Chofer', 'login': 'graf-driver', 'password': 'graf-driver-pass-1',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]})
        self.authenticate('graf-driver', 'graf-driver-pass-1')
        self.assertIn('error', self.call())

    def test_a_bus_user_gets_a_token_for_their_own_id(self):
        user = self.env['res.users'].create({
            'name': 'Lector', 'login': 'graf-reader', 'password': 'graf-reader-pass-1',
            'groups_id': [(6, 0, [self.env.ref('bus_tracking.group_bus_user').id])]})
        self.authenticate('graf-reader', 'graf-reader-pass-1')
        result = self.call()['result']
        self.assertTrue(result['configured'])
        self.assertEqual(decode(result['token'])[1]['sub'], 'odoo-%s' % user.id)


@tagged('post_install', '-at_install')
class TestGrafanaSettings(TransactionCase):

    def settings(self, **values):
        return self.env['res.config.settings'].create(values)

    def test_the_address_must_be_a_web_address(self):
        for bad in ('grafana', 'ftp://grafana.example.com', 'https://grafana.example.com/path'):
            with self.assertRaises(ValidationError, msg=bad):
                self.settings(bus_grafana_url=bad)
        self.settings(bus_grafana_url='https://grafana.example.com')
        self.settings(bus_grafana_url='http://localhost:3000')
        self.settings(bus_grafana_url='')

    def test_the_secret_needs_sixteen_characters(self):
        with self.assertRaises(ValidationError):
            self.settings(bus_grafana_secret='short')
        self.settings(bus_grafana_secret='x' * 16)

    def test_the_length_of_the_access_is_limited(self):
        for bad in (-1, 4, 1441):
            with self.assertRaises(ValidationError, msg=str(bad)):
                self.settings(bus_grafana_minutes=bad)
        self.settings(bus_grafana_minutes=5)
        self.settings(bus_grafana_minutes=1440)

    def test_the_menu_holds_both_dashboards(self):
        parent = self.env.ref('bus_tracking.menu_bus_indicators')
        self.assertEqual(set(parent.child_id.mapped('name')), {'Odoo dashboard', 'Grafana'})
        self.assertEqual(self.env.ref('bus_tracking.menu_bus_grafana').action.tag, 'bus_tracking.grafana')
