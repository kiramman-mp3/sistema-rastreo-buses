import base64
import importlib.util
from pathlib import Path
from unittest.mock import patch

import requests

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import BusCase
from .test_traccar_sync import fake_response

API = 'odoo.addons.bus_tracking.models.traccar_api.requests.'
PNG_MAGIC = b'\x89PNG'


@tagged('post_install', '-at_install')
class TestGpsSetup(BusCase):

    def setUp(self):
        super().setUp()
        icp = self.env['ir.config_parameter']
        icp.set_param('bus_tracking.traccar_url', 'http://traccar:8082')
        icp.set_param('bus_tracking.traccar_user', 'admin@example.com')
        icp.set_param('bus_tracking.traccar_password', 'secret')
        icp.set_param('bus_tracking.gps_url', 'https://gps.example.com/')
        self.new_bus = self.env['bus.vehicle'].create({'name': 'Bus 9'})

    def register(self, bus, device_id=42):
        with patch(API + 'post', return_value=fake_response({'id': device_id})) as post:
            bus.action_register_gps()
        return post

    # -- registering the phone ----------------------------------------------
    def test_register_creates_the_device_with_a_random_identifier(self):
        post = self.register(self.new_bus)
        sent = post.call_args.kwargs['json']
        self.assertEqual(post.call_args.args[0], 'http://traccar:8082/api/devices')
        self.assertEqual(sent['name'], 'Bus 9')
        self.assertRegex(sent['uniqueId'], r'^b-[0-9a-f]{16}$')
        self.assertEqual(self.new_bus.traccar_device_id, 42)
        self.assertEqual(self.new_bus.traccar_unique_id, sent['uniqueId'])

    def test_identifiers_are_different_for_every_bus(self):
        other = self.env['bus.vehicle'].create({'name': 'Bus 10'})
        self.register(self.new_bus, 42)
        self.register(other, 43)
        self.assertNotEqual(self.new_bus.traccar_unique_id, other.traccar_unique_id)

    def test_registering_twice_is_refused(self):
        with self.assertRaisesRegex(UserError, 'already has a GPS device'):
            self.bus.action_register_gps()      # BusCase's bus already has device 7

    def test_traccar_failure_leaves_the_bus_unregistered(self):
        with patch(API + 'post', return_value=fake_response({}, status=400)):
            with self.assertRaisesRegex(UserError, 'Traccar error 400'):
                self.new_bus.action_register_gps()
        self.assertFalse(self.new_bus.traccar_device_id)
        self.assertFalse(self.new_bus.traccar_unique_id)

    # -- link and QR ---------------------------------------------------------
    def test_tablet_qr_has_the_odoo_url_and_not_the_device_id(self):
        self.env['ir.config_parameter'].set_param(
            'web.base.url', 'https://busesuta2340.eastus2.cloudapp.azure.com/web')
        self.new_bus.invalidate_recordset(['tablet_setup_link', 'tablet_qr'])
        link = self.new_bus.tablet_setup_link
        self.assertTrue(link.startswith('uta-buses://setup?'))
        self.assertIn('odoo=https%3A%2F%2Fbusesuta2340.eastus2.cloudapp.azure.com', link)
        self.assertNotIn('/web', link)
        self.assertNotIn('id=', link)
        self.assertTrue(base64.b64decode(self.new_bus.tablet_qr).startswith(PNG_MAGIC))

    # -- the identifier is a credential ---------------------------------------
    def test_identifier_is_hidden_from_regular_users_and_visible_to_managers(self):
        Users = self.env['res.users']

        def group(xmlid):
            return self.env.ref(xmlid).id
        viewer = Users.create({
            'name': 'Viewer', 'login': 'viewer', 'groups_id': [(6, 0, [group('base.group_user'),
                                                                       group('bus_tracking.group_bus_user')])]})
        manager = Users.create({
            'name': 'Manager', 'login': 'manager', 'groups_id': [(6, 0, [group('base.group_user'),
                                                                         group('bus_tracking.group_bus_manager')])]})
        self.assertEqual(self.bus.with_user(viewer).name, 'Bus 1')
        with self.assertRaises(AccessError):
            self.bus.with_user(viewer).traccar_unique_id
        self.assertEqual(self.bus.with_user(manager).traccar_unique_id, 'BUS007')

    # -- first-run bootstrap of the Traccar account ---------------------------
    def test_bootstrap_registers_the_first_user_and_closes_registration(self):
        icp = self.env['ir.config_parameter']
        icp.set_param('bus_tracking.traccar_user', '')
        icp.set_param('bus_tracking.traccar_password', '')
        server = {'id': 1, 'registration': True, 'readonly': False}
        token = fake_response('tok_ABC-123=')
        token.text = 'tok_ABC-123=\n'                                 # Traccar answers plain text
        with patch(API + 'post', side_effect=[fake_response({'id': 1}), token]) as post, \
                patch(API + 'get', return_value=fake_response(dict(server))) as get, \
                patch(API + 'put', return_value=fake_response({})) as put:
            self.assertTrue(self.env['bus.traccar.api'].bootstrap_admin('boss@example.com', 'pw-123'))
        register, ask_token = post.call_args_list
        self.assertEqual(register.args[0], 'http://traccar:8082/api/users')
        self.assertEqual(register.kwargs['json']['email'], 'boss@example.com')
        self.assertIsNone(register.kwargs['auth'])                   # registration is anonymous
        self.assertEqual(ask_token.args[0], 'http://traccar:8082/api/session/token')
        self.assertEqual(ask_token.kwargs['auth'], ('boss@example.com', 'pw-123'))
        self.assertEqual(get.call_args.kwargs['auth'], ('boss@example.com', 'pw-123'))
        self.assertEqual(put.call_args.args[0], 'http://traccar:8082/api/server')
        self.assertEqual(put.call_args.kwargs['json'], dict(server, registration=False))
        self.assertEqual(icp.get_param('bus_tracking.traccar_user'), 'boss@example.com')
        # The password is swapped for a long-lived token, so a database copy does not hold it (S5).
        self.assertEqual(icp.get_param('bus_tracking.traccar_token'), 'tok_ABC-123=')
        self.assertFalse(icp.get_param('bus_tracking.traccar_password'))

    def test_an_existing_install_swaps_its_password_for_a_token(self):
        icp = self.env['ir.config_parameter']
        icp.set_param('bus_tracking.traccar_token', '')
        token = fake_response('x')
        token.text = 'tok123'
        with patch(API + 'post', return_value=token):
            self.assertTrue(self.env['bus.traccar.api'].switch_to_token())
        self.assertEqual(icp.get_param('bus_tracking.traccar_token'), 'tok123')
        self.assertFalse(icp.get_param('bus_tracking.traccar_password'))
        with patch(API + 'post') as post:
            self.assertFalse(self.env['bus.traccar.api'].switch_to_token())   # already on a token
        post.assert_not_called()

    def test_the_upgrade_keeps_the_password_when_traccar_does_not_answer(self):
        icp = self.env['ir.config_parameter']
        icp.set_param('bus_tracking.traccar_token', '')
        path = Path(__file__).resolve().parents[1] / 'migrations' / '16.0.1.7.0' / 'post-migrate.py'
        spec = importlib.util.spec_from_file_location('post_migrate_token', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch(API + 'post', side_effect=requests.ConnectionError('down')):
            module.migrate(self.env.cr, '16.0.1.6.0')                # must not raise
        self.assertEqual(icp.get_param('bus_tracking.traccar_password'), 'secret')

    def test_a_page_instead_of_a_token_keeps_the_password(self):
        icp = self.env['ir.config_parameter']
        icp.set_param('bus_tracking.traccar_token', '')
        page = fake_response('x')
        page.text = '<html>Bad gateway</html>'
        with patch(API + 'post', return_value=page), self.assertRaises(UserError):
            self.env['bus.traccar.api'].switch_to_token()
        self.assertEqual(icp.get_param('bus_tracking.traccar_password'), 'secret')

    def test_bootstrap_does_nothing_when_credentials_exist(self):
        with patch(API + 'post') as post:
            self.assertFalse(self.env['bus.traccar.api'].bootstrap_admin('boss@example.com', 'pw-123'))
        post.assert_not_called()
