from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from ..models.geo import simplify, thin
from .common import BusCase, traccar_position


@tagged('post_install', '-at_install')
class TestGeoSimplify(BusCase):

    def test_points_on_a_straight_line_collapse_to_the_ends(self):
        line = [[0.0, i * 0.0001] for i in range(10)]
        self.assertEqual(simplify(line, 5), [line[0], line[-1]])

    def test_a_corner_is_kept(self):
        line = [[0.0, 0.0], [0.0, 0.001], [0.001, 0.001]]
        self.assertEqual(len(simplify(line, 5)), 3)

    def test_thin_drops_the_cloud_of_a_parked_bus(self):
        cloud = [(-1.0, -78.0), (-1.000001, -78.000001), (-1.000002, -78.0), (-1.001, -78.0)]
        self.assertEqual(len(thin(cloud, 10)), 2)


@tagged('post_install', '-at_install')
class TestRecordTrack(BusCase):

    def feed(self, points):
        now = fields.Datetime.now().replace(microsecond=0)
        for i, (lat, lon) in enumerate(points):
            when = now - timedelta(minutes=len(points) - i)
            self.bus._apply_position(traccar_position(7, when.strftime('%Y-%m-%dT%H:%M:%SZ'), lat, lon, 5.0))
        return now

    def wizard(self):
        return self.env['bus.route.record'].create({
            'route_id': self.route.id, 'vehicle_id': self.bus.id,
            'date_from': fields.Datetime.now() - timedelta(hours=1), 'date_to': fields.Datetime.now()})

    def test_a_period_that_ends_before_it_starts_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env['bus.route.record'].create({
                'route_id': self.route.id, 'vehicle_id': self.bus.id,
                'date_from': fields.Datetime.now(), 'date_to': fields.Datetime.now() - timedelta(hours=1)})

    def test_the_recorded_track_replaces_the_straight_line(self):
        self.assertEqual(len(self.route._map_lines()[0]['points']), 3)
        # an L shaped trip: east and then north, with many points per leg
        trip = ([(-33.45, -70.66 + i * 0.0005) for i in range(10)]
                + [(-33.45 + i * 0.0005, -70.6555) for i in range(1, 10)])
        self.feed(trip)
        self.wizard().action_record()
        points = self.route._map_lines()[0]['points']
        self.assertEqual(self.route.track_points, len(points))
        self.assertEqual(len(points), 3)               # start, the corner, end
        self.assertEqual(points[0], [-33.45, -70.66])

    def test_too_few_positions_is_a_clear_error(self):
        with self.assertRaises(UserError):
            self.wizard().action_record()

    def test_clearing_returns_to_the_stops(self):
        self.feed([(-33.45, -70.66 + i * 0.001) for i in range(5)])
        self.wizard().action_record()
        self.route.action_clear_track()
        self.assertEqual(self.route.track_points, 0)
        self.assertEqual(len(self.route._map_lines()[0]['points']), 3)

    def test_a_broken_track_falls_back_to_the_stops(self):
        self.route.sudo().track_json = 'not json'
        self.assertEqual(len(self.route._map_lines()[0]['points']), 3)


@tagged('post_install', '-at_install')
class TestRecordTrackAccess(BusCase):

    def user(self, group):
        return self.env['res.users'].create({
            'name': group, 'login': group + '@example.org',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('bus_tracking.' + group).id])]})

    def test_a_manager_can_open_the_wizard_and_record(self):
        manager = self.user('group_bus_manager')
        now = fields.Datetime.now().replace(microsecond=0)
        for i in range(4):
            when = now - timedelta(minutes=4 - i)
            stamp = when.strftime('%Y-%m-%dT%H:%M:%SZ')
            self.bus._apply_position(traccar_position(7, stamp, -33.45, -70.66 + i * 0.001, 5.0))
        wizard = self.env['bus.route.record'].with_user(manager).create({
            'route_id': self.route.id, 'vehicle_id': self.bus.id,
            'date_from': now - timedelta(hours=1), 'date_to': now})
        wizard.action_record()
        self.assertGreater(self.route.track_points, 1)

    def test_a_plain_user_cannot_open_the_wizard(self):
        viewer = self.user('group_bus_user')
        with self.assertRaises(AccessError):
            self.env['bus.route.record'].with_user(viewer).create({
                'route_id': self.route.id, 'vehicle_id': self.bus.id})
