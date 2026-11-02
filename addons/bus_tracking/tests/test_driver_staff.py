from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .test_driver_auth import make_driver


@tagged('post_install', '-at_install')
class TestDriverStaff(TransactionCase):

    def setUp(self):
        super().setUp()
        self.route = self.env['bus.route'].create({'name': 'R', 'code': 'R1'})
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus 1', 'route_id': self.route.id})
        self.driver = make_driver(self.env)
        self.viewer = make_driver(self.env, login='visor', groups='bus_tracking.group_bus_user')
        self.manager = make_driver(self.env, login='gestor', groups='bus_tracking.group_bus_manager')
        self.shift = self.env['bus.shift'].create({
            'user_id': self.driver.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id})
        self.shift._assign_vehicle()
        self.incident = self.env['bus.incident'].create({
            'shift_id': self.shift.id, 'vehicle_id': self.bus.id, 'kind': 'traffic', 'note': 'Taco'})

    def test_staff_can_read_incidents_and_managers_can_delete_them(self):
        self.assertEqual(self.env['bus.incident'].with_user(self.viewer).search([]), self.incident)
        with self.assertRaises(AccessError):
            self.incident.with_user(self.viewer).unlink()
        self.incident.with_user(self.manager).unlink()
        self.assertFalse(self.incident.exists())

    def test_staff_mark_an_incident_as_seen_and_it_leaves_the_map_queue(self):
        self.assertIn(self.incident, self.env['bus.incident']._open_for_map())
        self.incident.with_user(self.viewer).action_acknowledge()
        self.assertEqual(self.incident.state, 'seen')
        self.assertEqual(self.incident.acknowledged_by, self.viewer)
        self.assertNotIn(self.incident, self.env['bus.incident']._open_for_map())
        first = self.incident.acknowledged_at
        self.incident.with_user(self.manager).action_acknowledge()       # the first person who saw it stays
        self.assertEqual((self.incident.acknowledged_by, self.incident.acknowledged_at), (self.viewer, first))

    def test_a_driver_cannot_mark_incidents_as_seen(self):
        with self.assertRaises(AccessError):
            self.incident.with_user(self.driver).action_acknowledge()

    def test_a_driver_cannot_read_incidents(self):
        with self.assertRaises(AccessError):
            self.env['bus.incident'].with_user(self.driver).search([])

    def test_new_incidents_are_pushed_once_to_the_managers(self):
        send = 'odoo.addons.bus_tracking.models.bus_push.BusPushSubscription._send_to_user'
        with patch(send, return_value=1) as sent:
            self.env['bus.incident']._cron_push()
            first = sent.call_count
            self.env['bus.incident']._cron_push()
        self.assertGreaterEqual(first, 1)
        self.assertEqual(sent.call_count, first)
        self.assertTrue(self.incident.notified)
        title = sent.call_args[0][1]['title']
        self.assertIn('Bus 1', title)
        self.assertEqual(sent.call_args[0][1]['body'], 'Taco')

    def test_a_manager_signs_the_tablet_out_and_closes_the_shift(self):
        raw = self.env['bus.driver.token']._issue(self.driver, 'Tablet 1')
        self.shift.with_user(self.manager).action_revoke_tablet()
        self.assertFalse(self.env['bus.driver.token']._user_for(raw))
        self.assertEqual(self.shift.state, 'done')
        self.assertFalse(self.bus.driver_id)

    def test_a_plain_user_cannot_sign_a_tablet_out(self):
        with self.assertRaises(AccessError):
            self.shift.with_user(self.viewer).action_revoke_tablet()
