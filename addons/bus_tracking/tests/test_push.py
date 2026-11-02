import base64
import json
import os
from unittest.mock import MagicMock, patch

import http_ece
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import WebPushException

from odoo.tests import HttpCase, TransactionCase, tagged

from ..models.bus_push import b64url, endpoint_allowed

GOOD_ENDPOINT = 'https://fcm.googleapis.com/fcm/send/abc123'

def new_device(user, endpoint=GOOD_ENDPOINT):
    """A browser: its key pair and auth secret, and the matching subscription row values."""
    receiver = ec.generate_private_key(ec.SECP256R1())
    public = receiver.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = os.urandom(16)
    return receiver, auth, {'user_id': user.id, 'endpoint': endpoint, 'p256dh': b64url(public), 'auth': b64url(auth)}


@tagged('post_install', '-at_install')
class TestPushModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Sub = self.env['bus.push.subscription']
        self.user = self.env['res.users'].create({
            'name': 'Mgr', 'login': 'mgr', 'email': 'mgr@example.org',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('bus_tracking.group_bus_manager').id])]})

    def test_only_the_big_push_services_are_accepted(self):
        for good in (GOOD_ENDPOINT,
                     'https://updates.push.services.mozilla.com/wpush/v2/xyz',
                     'https://web.push.apple.com/QXXX',
                     'https://wns2-par02p.notify.windows.com/w/?token=abc',
                     'https://fcm.googleapis.com:443/fcm/send/abc'):
            self.assertTrue(endpoint_allowed(good), good)
        for bad in ('', None, 'http://fcm.googleapis.com/fcm/send/abc',                 # not https
                    'https://localhost/x', 'https://127.0.0.1/x', 'https://10.0.0.5/x',
                    'https://fcm.googleapis.com.evil.com/x', 'https://evilfcm.googleapis.com.example/x',
                    'https://fcm.googleapis.com@evil.com/x', 'https://user@fcm.googleapis.com/x',
                    'https://fcm.googleapis.com:8443/x', 'https://notfcm.googleapis.org/x',
                    'ftp://fcm.googleapis.com/x', 'javascript:alert(1)', 'https://[::1]/x'):
            self.assertFalse(endpoint_allowed(bad), bad)

    def test_vapid_keys_are_created_once_and_look_right(self):
        private, public = self.Sub._vapid()
        self.assertTrue(private.startswith('-----BEGIN PRIVATE KEY-----'))
        raw = base64.urlsafe_b64decode(public + '=' * (-len(public) % 4))
        self.assertEqual((len(raw), raw[0]), (65, 4))                  # uncompressed P-256 point
        self.assertEqual(self.Sub._vapid(), (private, public))

    def test_a_real_message_is_encrypted_for_the_browser_and_signed(self):
        receiver, auth, values = new_device(self.user)
        sub = self.Sub.create(values)
        captured = {}

        def fake_post(url, data=None, headers=None, timeout=None):
            captured.update(url=url, data=data, headers=headers)
            return MagicMock(status_code=201, text='')

        payload = {'title': 'Speeding: Bus 12', 'body': '93 km/h', 'url': '/web', 'tag': 'bus-tracking'}
        with patch('pywebpush.requests.post', fake_post):
            self.assertTrue(sub._send_one(payload))
        self.assertEqual(captured['url'], GOOD_ENDPOINT)
        clear = http_ece.decrypt(captured['data'], private_key=receiver, auth_secret=auth, version='aes128gcm')
        self.assertEqual(json.loads(clear), payload)
        authorization = captured['headers']['Authorization']
        self.assertTrue(authorization.startswith('vapid t='), authorization)
        self.assertIn('k=' + self.Sub._vapid()[1], authorization)

    def test_gone_subscriptions_are_removed_and_other_errors_keep_them(self):
        for status, survives in ((410, False), (404, False), (500, True), (429, True)):
            _receiver, _auth, values = new_device(self.user, GOOD_ENDPOINT + str(status))
            sub = self.Sub.create(values)
            error = WebPushException('push failed', response=MagicMock(status_code=status))
            with patch('pywebpush.webpush', side_effect=error):
                self.assertFalse(sub._send_one({'title': 't'}))
            self.assertEqual(bool(sub.exists()), survives, status)

    def test_sending_to_a_user_counts_the_devices_that_accepted(self):
        for suffix in ('a', 'b'):
            self.Sub.create(new_device(self.user, GOOD_ENDPOINT + suffix)[2])
        outcomes = iter([True, False])
        with patch.object(type(self.Sub), '_send_one', lambda sub, payload: next(outcomes)):
            self.assertEqual(self.Sub._send_to_user(self.user, {'title': 't'}), 1)
        other = self.env['res.users'].create({'name': 'Other', 'login': 'other5'})
        self.assertEqual(self.Sub._send_to_user(other, {'title': 't'}), 0)

    def test_without_the_library_push_is_skipped_quietly(self):
        self.Sub.create(new_device(self.user)[2])
        with patch.object(type(self.Sub), '_available', lambda model: False):
            self.assertEqual(self.Sub._send_to_user(self.user, {'title': 't'}), 0)

    def test_a_device_can_only_be_registered_once(self):
        values = new_device(self.user)[2]
        self.Sub.create(values)
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.Sub.create(values)


@tagged('post_install', '-at_install')
class TestPushEndpoints(HttpCase):

    def setUp(self):
        super().setUp()
        Users = self.env['res.users']
        group = lambda xmlid: self.env.ref(xmlid).id
        self.viewer = Users.create({'name': 'Viewer', 'login': 'viewer5', 'password': 'viewer5-pass',
                                    'groups_id': [(6, 0, [group('base.group_user'), group('bus_tracking.group_bus_user')])]})
        self.manager = Users.create({'name': 'Manager', 'login': 'manager5', 'password': 'manager5-pass',
                                     'groups_id': [(6, 0, [group('base.group_user'), group('bus_tracking.group_bus_manager')])]})

    def call(self, path, **params):
        resp = self.url_open(path, data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params}),
                             headers={'Content-Type': 'application/json'})
        return resp.json()

    def subscriptions(self):
        return self.env['bus.push.subscription'].search([])

    def test_the_service_worker_is_served_as_javascript_without_caching(self):
        resp = self.url_open('/bus_tracking/sw.js')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('application/javascript', resp.headers['Content-Type'])
        self.assertEqual(resp.headers['Cache-Control'], 'no-cache')
        self.assertIn('addEventListener("push"', resp.text)

    def test_only_managers_can_use_the_push_endpoints(self):
        self.authenticate('viewer5', 'viewer5-pass')
        for path in ('state', 'subscribe', 'unsubscribe', 'test'):
            self.assertIn('error', self.call('/bus_tracking/push/' + path), path)
        self.authenticate(None, None)
        self.assertIn('error', self.call('/bus_tracking/push/state'))

    def test_state_gives_the_browser_the_public_key(self):
        self.authenticate('manager5', 'manager5-pass')
        result = self.call('/bus_tracking/push/state')['result']
        self.assertTrue(result['available'])
        self.assertEqual(result['key'], self.env['bus.push.subscription']._vapid()[1])
        self.assertEqual((result['subscribed'], result['devices']), (False, 0))

    def test_subscribing_stores_the_device_and_state_sees_it(self):
        self.authenticate('manager5', 'manager5-pass')
        _r, _a, values = new_device(self.manager)
        result = self.call('/bus_tracking/push/subscribe', endpoint=values['endpoint'],
                           keys={'p256dh': values['p256dh'], 'auth': values['auth']}, user_agent='Firefox')['result']
        self.assertEqual(result, {'ok': True})
        self.assertEqual(self.subscriptions().user_id, self.manager)
        state = self.call('/bus_tracking/push/state', endpoint=values['endpoint'])['result']
        self.assertEqual((state['subscribed'], state['devices']), (True, 1))
        # registering the same browser again updates it instead of failing
        self.call('/bus_tracking/push/subscribe', endpoint=values['endpoint'],
                  keys={'p256dh': values['p256dh'], 'auth': values['auth']}, user_agent='Firefox 2')
        self.assertEqual(len(self.subscriptions()), 1)

    def test_bad_endpoints_and_keys_are_refused(self):
        self.authenticate('manager5', 'manager5-pass')
        keys = {'p256dh': 'x' * 87, 'auth': 'y' * 22}
        self.assertEqual(self.call('/bus_tracking/push/subscribe', endpoint='https://evil.example/x', keys=keys)['result'],
                         {'ok': False, 'error': 'endpoint'})
        self.assertEqual(self.call('/bus_tracking/push/subscribe', endpoint='http://fcm.googleapis.com/x', keys=keys)['result']['ok'], False)
        for bad_keys in (None, {}, {'p256dh': 'x'}, {'p256dh': 'x' * 500, 'auth': 'y'}, {'p256dh': 1, 'auth': 2}):
            self.assertEqual(self.call('/bus_tracking/push/subscribe', endpoint=GOOD_ENDPOINT, keys=bad_keys)['result'],
                             {'ok': False, 'error': 'keys'})
        self.assertFalse(self.subscriptions())

    def test_unsubscribing_only_removes_the_callers_device(self):
        _r, _a, mine = new_device(self.manager, GOOD_ENDPOINT + 'mine')
        _r, _a, theirs = new_device(self.viewer, GOOD_ENDPOINT + 'theirs')
        self.env['bus.push.subscription'].create([mine, theirs])
        self.authenticate('manager5', 'manager5-pass')
        self.call('/bus_tracking/push/unsubscribe', endpoint=mine['endpoint'])
        self.call('/bus_tracking/push/unsubscribe', endpoint=theirs['endpoint'])
        self.assertEqual(self.subscriptions().mapped('endpoint'), [theirs['endpoint']])

    def test_the_test_button_pushes_to_the_callers_devices(self):
        self.authenticate('manager5', 'manager5-pass')
        calls = []
        with patch.object(type(self.env['bus.push.subscription']), '_send_to_user',
                          lambda model, user, payload: calls.append((user.login, payload['title'])) or 2):
            result = self.call('/bus_tracking/push/test')['result']
        self.assertEqual(result, {'sent': 2})
        self.assertEqual(calls, [('manager5', 'Test notification')])


@tagged('post_install', '-at_install')
class TestPushQueue(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Sub = self.env['bus.push.subscription']
        self.manager = self.env['res.users'].create({
            'name': 'Mgr Queue', 'login': 'mgr_queue',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('bus_tracking.group_bus_manager').id])]})
        self.Sub.create(new_device(self.manager)[2])
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus Q'})

    def test_a_network_error_does_not_stop_the_queue_nor_repeat_it(self):
        import requests
        self.env['bus.alert'].search([]).write({'notified': True})
        alert = self.env['bus.alert'].create({
            'vehicle_id': self.bus.id, 'kind': 'speeding', 'start_time': '2026-10-26 12:00:00'})
        with patch('pywebpush.webpush', side_effect=requests.ConnectionError('down')) as sent:
            self.env['bus.alert']._cron_push()        # must not raise
            self.assertTrue(alert.notified)
            calls = sent.call_count
            self.env['bus.alert']._cron_push()
            self.assertEqual(sent.call_count, calls)
        self.assertTrue(self.Sub.search([('user_id', '=', self.manager.id)]))
