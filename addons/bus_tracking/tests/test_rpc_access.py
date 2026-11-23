"""Public methods of abstract models and wizards are reachable over RPC (`/web/dataset/call_kw`) by anyone with a
session, drivers (portal users) included, and Odoo checks no access rights before running them. The ones that reach
Traccar, read the indicators with raw SQL or act as the system must check who calls them."""
import json
from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError
from odoo.tests import HttpCase, TransactionCase, tagged

API = 'odoo.addons.bus_tracking.models.traccar_api.requests.'


def traccar_answer(payload):
    resp = MagicMock(status_code=200, ok=True, content=b'x')
    resp.json.return_value = payload
    return resp


class AccessMixin:

    @classmethod
    def _make_users(cls):
        icp = cls.env['ir.config_parameter'].sudo()
        icp.set_param('bus_tracking.traccar_url', 'http://traccar:8082')
        icp.set_param('bus_tracking.traccar_token', 'secret-token')
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.driver = Users.with_context(default_is_bus_driver=True).create({
            'name': 'Chofer RPC', 'login': 'rpc_driver', 'password': 'rpc-driver-pass-1'})
        cls.staff = Users.create({
            'name': 'Operador RPC', 'login': 'rpc_staff', 'password': 'rpc-staff-pass-1',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('bus_tracking.group_bus_user').id])]})
        cls.manager = Users.create({
            'name': 'Gestor RPC', 'login': 'rpc_manager', 'password': 'rpc-manager-pass-1',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id,
                                  cls.env.ref('bus_tracking.group_bus_manager').id])]})


@tagged('post_install', '-at_install')
class TestRpcAccess(AccessMixin, HttpCase):
    """The attack itself: a driver signs in on the web and calls the methods over RPC."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._make_users()

    def call_kw(self, model, method, args=None, kwargs=None):
        resp = self.url_open('/web/dataset/call_kw/%s/%s' % (model, method), data=json.dumps({
            'jsonrpc': '2.0', 'method': 'call',
            'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}),
            headers={'Content-Type': 'application/json'})
        return resp.json()

    def assertRefused(self, answer):
        self.assertIn('error', answer)
        self.assertEqual(answer['error']['data']['name'], 'odoo.exceptions.AccessError')

    def test_a_driver_cannot_read_the_devices_nor_their_identifiers(self):
        self.authenticate('rpc_driver', 'rpc-driver-pass-1')
        with patch(API + 'get') as get:
            self.assertRefused(self.call_kw('bus.traccar.api', 'get_devices'))
            self.assertRefused(self.call_kw('bus.traccar.api', 'get_latest_positions'))
        get.assert_not_called()

    def test_a_driver_cannot_create_devices_in_traccar(self):
        self.authenticate('rpc_driver', 'rpc-driver-pass-1')
        with patch(API + 'post') as post:
            self.assertRefused(self.call_kw('bus.traccar.api', 'create_device', ['Falso', 'b-123']))
        post.assert_not_called()

    def test_a_driver_cannot_send_the_server_to_another_address(self):
        self.authenticate('rpc_driver', 'rpc-driver-pass-1')
        with patch(API + 'get') as get:
            self.assertRefused(self.call_kw('bus.traccar.api', 'get_devices', kwargs={'conf': {
                'url': 'http://169.254.169.254', 'user': '', 'password': '', 'token': 'x'}}))
        get.assert_not_called()

    def test_a_driver_cannot_read_the_indicators(self):
        self.authenticate('rpc_driver', 'rpc-driver-pass-1')
        self.assertRefused(self.call_kw('bus.kpi', 'compute'))

    def test_a_driver_cannot_fill_the_database_with_simulated_trips(self):
        self.authenticate('rpc_driver', 'rpc-driver-pass-1')
        before = self.env['bus.trip'].search_count([])
        self.assertRefused(self.call_kw('bus.trip.simulate', 'action_demo_set', [[]]))
        self.assertEqual(self.env['bus.trip'].search_count([]), before)

    def test_a_driver_cannot_delete_a_badge_shown_to_a_manager(self):
        badge = self.env['bus.driver.badge'].sudo().create({'user_id': self.driver.id, 'link': 'uta-buses://x'})
        self.authenticate('rpc_driver', 'rpc-driver-pass-1')
        self.assertRefused(self.call_kw('bus.driver.badge', 'action_done', [badge.ids]))
        self.assertTrue(badge.exists())

    def test_the_transport_team_still_reads_the_indicators(self):
        self.authenticate('rpc_staff', 'rpc-staff-pass-1')
        answer = self.call_kw('bus.kpi', 'compute')
        self.assertNotIn('error', answer)
        self.assertEqual(len(answer['result']['metrics']), 12)


@tagged('post_install', '-at_install')
class TestTraccarApiAccess(AccessMixin, TransactionCase):
    """Who may still reach Traccar after the check: the system, managers and the administrators of Settings."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._make_users()

    def test_the_transport_team_without_management_is_refused(self):
        with patch(API + 'get') as get, self.assertRaises(AccessError):
            self.env['bus.traccar.api'].with_user(self.staff).get_devices()
        get.assert_not_called()

    def test_a_manager_reaches_traccar(self):
        with patch(API + 'get', return_value=traccar_answer([{'id': 1}])) as get:
            self.assertEqual(self.env['bus.traccar.api'].with_user(self.manager).get_devices(), [{'id': 1}])
        get.assert_called_once()

    def test_the_system_reaches_traccar(self):
        # The crons and the webhook run as the system.
        with patch(API + 'get', return_value=traccar_answer([])) as get:
            self.assertEqual(self.env['bus.traccar.api'].sudo().get_latest_positions(), [])
        get.assert_called_once()

    def test_an_administrator_tests_the_connection_from_settings(self):
        admin = self.env.ref('base.user_admin')
        admin.groups_id = [(3, self.env.ref('bus_tracking.group_bus_manager').id)]
        self.assertFalse(admin.has_group('bus_tracking.group_bus_manager'))
        with patch(API + 'get', return_value=traccar_answer([])):
            self.env['bus.traccar.api'].with_user(admin).get_devices()

    def test_the_transport_team_still_reads_the_indicators(self):
        self.assertEqual(len(self.env['bus.kpi'].with_user(self.staff).compute()['metrics']), 12)

    def test_a_driver_is_refused_the_indicators_in_python_too(self):
        with self.assertRaises(AccessError):
            self.env['bus.kpi'].with_user(self.driver).compute()
