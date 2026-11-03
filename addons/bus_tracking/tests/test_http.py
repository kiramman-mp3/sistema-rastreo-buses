import json
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged

from .common import traccar_position

WEBHOOK = '/bus_tracking/traccar/webhook'


@tagged('post_install', '-at_install')
class TestHttp(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].set_param('bus_tracking.webhook_secret', 's3cret')
        # These tests are about the webhook itself, not about shifts (see test_ingest).
        self.env['ir.config_parameter'].set_param('bus_tracking.accept_without_shift', '1')
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus 1', 'traccar_device_id': 7})
        self.body = json.dumps({
            'position': traccar_position(7, '2026-10-26T12:00:00Z', -33.47, -70.62, speed_knots=5.0),
            'device': {'id': 7},
        })

    def post(self, query='?secret=s3cret', data=None):
        return self.url_open(WEBHOOK + query, data=self.body if data is None else data,
                             headers={'Content-Type': 'application/json'})

    def positions(self):
        return self.env['bus.position'].search_count([('vehicle_id', '=', self.bus.id)])

    def test_webhook_rejects_missing_or_wrong_secret(self):
        self.assertEqual(self.post(query='').status_code, 403)
        self.assertEqual(self.post(query='?secret=nope').status_code, 403)
        self.assertEqual(self.positions(), 0)

    def test_webhook_is_closed_when_no_secret_is_configured(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.webhook_secret', '')
        self.assertEqual(self.post(query='?secret=').status_code, 403)
        self.assertEqual(self.post(query='').status_code, 403)

    def test_webhook_stores_position(self):
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.positions(), 1)

    def test_webhook_accepts_secret_in_header(self):
        for headers in ({'X-Webhook-Secret': 's3cret'}, {'Authorization': 'Bearer s3cret'}):
            resp = self.url_open(WEBHOOK, data=self.body,
                                 headers=dict(headers, **{'Content-Type': 'application/json'}))
            self.assertEqual(resp.status_code, 200, headers)
        bad = self.url_open(WEBHOOK, data=self.body,
                            headers={'X-Webhook-Secret': 'nope', 'Content-Type': 'application/json'})
        self.assertEqual(bad.status_code, 403)

    def test_health_ok_without_buses_or_with_fresh_position(self):
        self.bus.unlink()
        self.assertEqual(self.url_open('/bus_tracking/health').status_code, 200)
        bus = self.env['bus.vehicle'].create({'name': 'B', 'traccar_device_id': 9})
        self.assertEqual(self.url_open('/bus_tracking/health').status_code, 503)
        bus.write({'last_fix_time': fields.Datetime.now()})
        resp = self.url_open('/bus_tracking/health')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ok')

    def test_health_goes_stale_and_can_be_disabled(self):
        self.bus.write({'last_fix_time': fields.Datetime.now() - timedelta(minutes=11)})
        self.assertEqual(self.url_open('/bus_tracking/health').status_code, 503)
        stale = self.url_open('/bus_tracking/health').json()
        self.assertEqual(stale['status'], 'stale')
        self.assertRegex(stale['version'], r'^16\.0\.\d+\.\d+\.\d+$')  # which release is running
        self.env['ir.config_parameter'].set_param('bus_tracking.stale_minutes', '30')
        self.assertEqual(self.url_open('/bus_tracking/health').status_code, 200)
        self.env['ir.config_parameter'].set_param('bus_tracking.stale_minutes', '0')
        self.bus.write({'last_fix_time': fields.Datetime.now() - timedelta(days=3)})
        self.assertEqual(self.url_open('/bus_tracking/health').status_code, 200)

    def test_webhook_rejects_invalid_body(self):
        self.assertEqual(self.post(data='not json').status_code, 400)

    def test_webhook_rejects_out_of_range_latitude(self):
        body = json.dumps({
            'position': traccar_position(7, '2026-10-26T12:00:00Z', 95.0, -70.62),
            'device': {'id': 7},
        })
        self.assertEqual(self.post(data=body).status_code, 400)
        self.assertEqual(self.positions(), 0)

    def test_webhook_rejects_non_numeric_latitude(self):
        body = json.dumps({
            'position': traccar_position(7, '2026-10-26T12:00:00Z', 'abc', -70.62),
            'device': {'id': 7},
        })
        self.assertEqual(self.post(data=body).status_code, 400)
        self.assertEqual(self.positions(), 0)

    def test_webhook_rejects_invalid_fixtime(self):
        body = json.dumps({
            'position': traccar_position(7, 'ayer', -33.47, -70.62),
            'device': {'id': 7},
        })
        self.assertEqual(self.post(data=body).status_code, 400)
        self.assertEqual(self.positions(), 0)

    def test_webhook_rejects_get(self):
        self.assertEqual(self.url_open(WEBHOOK + '?secret=s3cret').status_code, 405)

    def test_live_endpoint_requires_a_session(self):
        resp = self.url_open('/bus_tracking/live', data=json.dumps(
            {'jsonrpc': '2.0', 'method': 'call', 'params': {}}),
            headers={'Content-Type': 'application/json'})
        self.assertIn('error', resp.json())

    def test_live_endpoint_returns_buses_and_routes(self):
        route = self.env['bus.route'].create({
            'name': 'R', 'code': 'R1',
            'stop_ids': [(0, 0, {'name': 'A', 'latitude': -33.45, 'longitude': -70.66})]})
        self.bus.route_id = route
        self.bus._apply_position(traccar_position(7, '2026-10-26T12:00:00Z', -33.47, -70.62))
        self.authenticate('admin', 'admin')
        resp = self.url_open('/bus_tracking/live', data=json.dumps(
            {'jsonrpc': '2.0', 'method': 'call', 'params': {}}),
            headers={'Content-Type': 'application/json'})
        result = resp.json()['result']
        self.assertEqual([v['name'] for v in result['vehicles']], ['Bus 1'])
        self.assertEqual(result['routes'][0]['stops'][0]['name'], 'A')

    def test_live_endpoint_includes_open_alerts(self):
        self.bus._apply_position(traccar_position(
            7, fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'), -33.47, -70.62, speed_knots=50.0))
        self.authenticate('admin', 'admin')
        resp = self.url_open('/bus_tracking/live', data=json.dumps(
            {'jsonrpc': '2.0', 'method': 'call', 'params': {}}),
            headers={'Content-Type': 'application/json'})
        result = resp.json()['result']
        self.assertEqual(result['vehicles'][0]['alerts'], ['speeding'])
        self.assertEqual(result['alert_labels']['speeding'], 'Speeding')

    def test_landing_is_public_and_login_is_themed(self):
        landing = self.url_open('/')
        self.assertEqual(landing.status_code, 200)
        self.assertIn('¿Dónde viene tu bus?', landing.text)
        self.assertIn('/web/login', landing.text)
        self.assertIn('o_bus_login_shell', self.url_open('/web/login').text)

    def test_landing_is_skipped_for_signed_in_users(self):
        self.authenticate('admin', 'admin')
        resp = self.url_open('/', allow_redirects=False)
        self.assertEqual(resp.status_code, 303)
        self.assertIn('/web', resp.headers['Location'])

    def track(self, **params):
        self.authenticate('admin', 'admin')
        return self.url_open('/bus_tracking/track', data=json.dumps(
            {'jsonrpc': '2.0', 'method': 'call', 'params': params}),
            headers={'Content-Type': 'application/json'}).json()

    def test_track_is_bounded_and_validated(self):
        self.bus._apply_position(traccar_position(
            7, fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'), -33.47, -70.62))
        self.assertEqual(self.track(vehicle_id=self.bus.id, hours=10 ** 9)['result'], [[-33.47, -70.62]])
        self.assertEqual(len(self.track(vehicle_id=self.bus.id, hours='nan')['result']), 1)
        bad = self.track(vehicle_id='x')
        self.assertIn('error', bad)
        self.assertNotIn('Overflow', json.dumps(bad))

    def test_webhook_still_accepts_the_secret_in_the_url_for_now(self):
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.positions(), 1)

    def rpc(self, path, **params):
        return self.url_open(path, data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params}),
                             headers={'Content-Type': 'application/json'}).json()

    def test_the_stop_picker_loads_and_saves_through_http(self):
        route = self.env['bus.route'].create({
            'name': 'R', 'code': 'R1', 'stop_ids': [(0, 0, {'name': 'A', 'latitude': -1.24, 'longitude': -78.62})]})
        self.authenticate('admin', 'admin')
        data = self.rpc('/bus_tracking/stop/load', route_id=route.id)['result']
        self.assertEqual([s['name'] for s in data['stops']], ['A'])
        self.assertTrue(data['tile_url'].startswith('https://'))
        saved = self.rpc('/bus_tracking/stop/save', route_id=route.id, stop_id=False, name='B',
                         latitude=-1.25, longitude=-78.63, radius=40)['result']
        self.assertEqual(self.env['bus.route.stop'].browse(saved['id']).name, 'B')

    def test_an_incident_is_marked_as_seen_through_http(self):
        route = self.env['bus.route'].create({'name': 'R', 'code': 'R1'})
        driver = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Chofer HTTP', 'login': 'chofer_http', 'password': 'x' * 12,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id,
                                  self.env.ref('bus_tracking.group_bus_driver').id])]})
        shift = self.env['bus.shift'].create({'user_id': driver.id, 'vehicle_id': self.bus.id, 'route_id': route.id})
        incident = self.env['bus.incident'].create({'shift_id': shift.id, 'vehicle_id': self.bus.id, 'kind': 'sos'})
        self.authenticate('admin', 'admin')
        self.assertEqual(self.rpc('/bus_tracking/incident/ack', incident_id=incident.id)['result']['ok'], True)
        self.assertTrue(incident.acknowledged_at)
        self.assertEqual(self.rpc('/bus_tracking/incident/ack', incident_id=999999)['result'], {'ok': False})
