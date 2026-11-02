from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import BusCase, traccar_position

REQUESTS_GET = 'odoo.addons.bus_tracking.models.traccar_api.requests.get'


def fake_response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.ok = status < 400
    resp.text = str(payload)
    resp.json.return_value = payload
    return resp


@tagged('post_install', '-at_install')
class TestTraccarSync(BusCase):

    def setUp(self):
        super().setUp()
        icp = self.env['ir.config_parameter']
        icp.set_param('bus_tracking.traccar_url', 'http://traccar:8082/')
        icp.set_param('bus_tracking.traccar_user', 'admin@example.com')
        icp.set_param('bus_tracking.traccar_password', 'secret')
        icp.set_param('bus_tracking.traccar_token', '')
        icp.set_param('bus_tracking.accept_without_shift', '1')

    def test_is_configured(self):
        api = self.env['bus.traccar.api']
        self.assertTrue(api.is_configured())
        self.env['ir.config_parameter'].set_param('bus_tracking.traccar_url', '')
        self.assertFalse(api.is_configured())

    def test_cron_applies_latest_positions(self):
        positions = [
            traccar_position(7, '2026-10-26T12:00:00Z', -33.47, -70.62, speed_knots=10.0),
            traccar_position(999, '2026-10-26T12:00:00Z', -33.0, -70.0),  # no bus linked
        ]
        with patch(REQUESTS_GET, return_value=fake_response(positions)) as get:
            self.env['bus.vehicle']._cron_sync_positions()
        self.assertEqual(get.call_args.args[0], 'http://traccar:8082/api/positions')
        self.assertEqual(get.call_args.kwargs['auth'], ('admin@example.com', 'secret'))
        self.assertEqual(self.env['bus.position'].search_count([('vehicle_id', '=', self.bus.id)]), 1)
        self.assertEqual(self.env['bus.position'].search_count([]), 1)

    def test_token_takes_precedence_over_password(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.traccar_token', 'tok')
        with patch(REQUESTS_GET, return_value=fake_response([])) as get:
            self.env['bus.vehicle']._cron_sync_positions()
        self.assertEqual(get.call_args.kwargs['headers']['Authorization'], 'Bearer tok')
        self.assertIsNone(get.call_args.kwargs['auth'])

    def test_cron_survives_traccar_errors(self):
        with patch(REQUESTS_GET, return_value=fake_response({}, status=500)):
            self.env['bus.vehicle']._cron_sync_positions()  # must not raise
        self.assertFalse(self.env['bus.position'].search_count([]))

    def test_cron_does_nothing_when_unconfigured(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.traccar_url', '')
        with patch(REQUESTS_GET) as get:
            self.env['bus.vehicle']._cron_sync_positions()
        get.assert_not_called()

    def test_bad_credentials_raise_a_clear_error(self):
        with patch(REQUESTS_GET, return_value=fake_response({}, status=401)):
            with self.assertRaisesRegex(UserError, 'credentials'):
                self.env['bus.traccar.api'].get_devices()
