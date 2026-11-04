from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import BusCase, traccar_position
from .test_traccar_sync import REQUESTS_GET, fake_response

NOW_FIX = '2026-10-26T12:00:00Z'


@tagged('post_install', '-at_install')
class TestDemoReport(BusCase):
    """A bus that reports for a demonstration with Traccar Client: only that bus, only for a while."""

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].set_param('bus_tracking.accept_without_shift', '0')
        self.payload = {'position': traccar_position(7, NOW_FIX, -33.47, -70.62)}

    def stored(self):
        return self.env['bus.position'].search_count([('vehicle_id', '=', self.bus.id)])

    def test_without_the_mark_a_position_without_shift_is_dropped(self):
        self.assertFalse(self.bus.demo_report)
        self.assertFalse(self.env['bus.vehicle']._process_traccar_payload(self.payload))
        self.assertEqual(self.stored(), 0)

    def test_with_the_mark_a_position_without_shift_is_stored(self):
        self.bus.action_start_demo_report()
        self.assertTrue(self.bus.demo_report)
        self.assertTrue(self.env['bus.vehicle']._process_traccar_payload(self.payload))
        self.assertEqual(self.stored(), 1)
        self.assertEqual(self.bus.last_fix_time.isoformat(), '2026-10-26T12:00:00')

    def test_the_mark_lasts_eight_hours_and_then_switches_itself_off(self):
        self.bus.action_start_demo_report()
        self.assertAlmostEqual(self.bus.demo_report_until, fields.Datetime.now() + timedelta(hours=8),
                               delta=timedelta(seconds=10))
        self.bus.demo_report_until = fields.Datetime.now() - timedelta(minutes=1)
        self.assertFalse(self.bus.demo_report)
        self.assertFalse(self.env['bus.vehicle']._process_traccar_payload(self.payload))
        self.assertEqual(self.stored(), 0)

    def test_stopping_it_goes_back_to_needing_a_shift(self):
        self.bus.action_start_demo_report()
        self.bus.action_stop_demo_report()
        self.assertFalse(self.bus.demo_report)
        self.assertFalse(self.bus.demo_report_until)
        self.assertFalse(self.env['bus.vehicle']._process_traccar_payload(self.payload))

    def test_it_only_opens_the_marked_bus(self):
        other = self.env['bus.vehicle'].create({'name': 'Bus 2', 'traccar_device_id': 8, 'traccar_unique_id': 'BUS008'})
        self.bus.action_start_demo_report()
        self.assertFalse(other.demo_report)
        self.assertFalse(self.env['bus.vehicle']._process_traccar_payload(
            {'position': traccar_position(8, NOW_FIX, -33.47, -70.62)}))
        self.assertTrue(self.env['bus.vehicle']._process_traccar_payload(self.payload))

    def test_a_bus_without_a_gps_device_cannot_be_marked(self):
        bare = self.env['bus.vehicle'].create({'name': 'Bus sin GPS'})
        with self.assertRaises(UserError):
            bare.action_start_demo_report()
        self.assertFalse(bare.demo_report_until)

    def test_only_managers_can_start_or_stop_it(self):
        viewer = self.env['res.users'].create({
            'name': 'Lector', 'login': 'demo-viewer',
            'groups_id': [(6, 0, [self.env.ref('bus_tracking.group_bus_user').id])]})
        for action in ('action_start_demo_report', 'action_stop_demo_report'):
            with self.assertRaises(AccessError):
                getattr(self.bus.with_user(viewer), action)()
        self.assertFalse(self.bus.demo_report)

    def test_the_pull_sync_honours_the_mark_too(self):
        icp = self.env['ir.config_parameter']
        icp.set_param('bus_tracking.traccar_url', 'http://traccar:8082/')
        icp.set_param('bus_tracking.traccar_user', 'admin@example.com')
        icp.set_param('bus_tracking.traccar_password', 'secret')
        positions = [traccar_position(7, NOW_FIX, -33.47, -70.62)]
        with patch(REQUESTS_GET, return_value=fake_response(positions)):
            self.env['bus.vehicle']._cron_sync_positions()
            self.assertEqual(self.stored(), 0)
            self.bus.action_start_demo_report()
            self.env['bus.vehicle']._cron_sync_positions()
        self.assertEqual(self.stored(), 1)

    def test_the_audit_does_not_count_what_was_dropped_on_purpose(self):
        when = fields.Datetime.now() + timedelta(minutes=5)
        self.assertFalse(self.bus._expects_position(when))
        self.bus.action_start_demo_report()
        self.assertTrue(self.bus._expects_position(when))
        self.assertFalse(self.bus._expects_position(when + timedelta(hours=9)))     # after the mark ran out

    def test_the_mark_is_not_copied_with_the_bus(self):
        self.bus.action_start_demo_report()
        copy = self.bus.copy({'name': 'Bus copia'})
        self.assertFalse(copy.demo_report_until)
