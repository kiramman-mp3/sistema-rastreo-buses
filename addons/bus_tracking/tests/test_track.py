import base64
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from ..models.geo import simplify, thin
from .common import STOPS, BusCase, traccar_position


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


GPX_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'


def gpx_with(*items, ns='http://www.topografix.com/GPX/1/1'):
    return ('%s<gpx version="1.1" xmlns="%s">%s</gpx>' % (GPX_HEADER, ns, ''.join(items))).encode()


def trk(points):
    return '<trk><trkseg>%s</trkseg></trk>' % ''.join(
        '<trkpt lat="%s" lon="%s"><ele>2500</ele></trkpt>' % p for p in points)


@tagged('post_install', '-at_install')
class TestGpx(BusCase):

    LINE = [(-1.2400 + i * 0.0005, -78.6200 + i * 0.0003) for i in range(40)]

    def load(self, data, create_stops=False, route=None):
        return self.env['bus.route.gpx'].create({
            'route_id': (route or self.route).id,
            'gpx_file': base64.b64encode(data),
            'gpx_filename': 'ruta.gpx',
            'create_stops': create_stops,
        }).action_load()

    def test_a_track_becomes_the_line_of_the_route(self):
        self.load(gpx_with(trk(self.LINE)))
        points = self.route._recorded_points()
        self.assertGreaterEqual(len(points), 2)
        self.assertEqual(points[0], [round(self.LINE[0][0], 6), round(self.LINE[0][1], 6)])
        self.assertEqual(points[-1], [round(self.LINE[-1][0], 6), round(self.LINE[-1][1], 6)])
        self.assertEqual(self.route._map_lines()[0]['points'], points)

    def test_the_longest_track_wins_and_files_without_namespace_work(self):
        short = [(-1.2, -78.6), (-1.2001, -78.6001)]
        data = gpx_with(trk(short), trk(self.LINE), ns='')
        data = data.replace(b' xmlns=""', b'')
        self.load(data)
        self.assertEqual(self.route._recorded_points()[0][0], round(self.LINE[0][0], 6))

    def test_a_planned_route_is_used_when_there_is_no_track(self):
        rte = '<rte>%s</rte>' % ''.join('<rtept lat="%s" lon="%s"/>' % p for p in self.LINE)
        self.load(gpx_with(rte))
        self.assertGreaterEqual(self.route.track_points, 2)

    def test_waypoints_become_stops_only_on_a_route_without_stops(self):
        wpts = ''.join('<wpt lat="%s" lon="%s"><name>%s</name></wpt>' % (lat, lon, name)
                       for name, (lat, lon) in (('Terminal', self.LINE[0]), ('Plaza', self.LINE[20]), ('', self.LINE[-1])))
        data = gpx_with(wpts, trk(self.LINE))
        self.load(data, create_stops=True)           # this route already has stops: untouched
        self.assertEqual(len(self.route.stop_ids), 3)
        self.assertEqual(self.route.stop_ids.mapped('name'), [name for name, _lat, _lon in STOPS])
        empty = self.env['bus.route'].create({'name': 'Nueva', 'code': 'N1'})
        self.load(data, create_stops=True, route=empty)
        self.assertEqual(empty.stop_ids.mapped('name'), ['Terminal', 'Plaza', 'Stop 3'])
        self.assertEqual(empty.stop_ids.mapped('sequence'), [10, 20, 30])

    def test_bad_files_are_refused_with_a_message_and_change_nothing(self):
        self.route.track_json = '[[1,1],[2,2]]'
        for data in (b'not xml at all', b'<html/>', gpx_with('<wpt lat="1" lon="1"/>'),
                     gpx_with(trk([(95.0, 10.0), (96.0, 11.0)])), gpx_with(trk([(1.0, 1.0)]))):
            with self.assertRaises(UserError):
                self.load(data)
        self.assertEqual(self.route.track_json, '[[1,1],[2,2]]')

    def test_entities_are_not_expanded(self):
        bomb = (GPX_HEADER + '<!DOCTYPE gpx [<!ENTITY a "AAAAAAAAAA"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;">]>'
                '<gpx><trk><trkseg><trkpt lat="1" lon="1"><name>&b;</name></trkpt>'
                '<trkpt lat="1.001" lon="1.001"/></trkseg></trk></gpx>').encode()
        self.load(bomb)
        self.assertEqual(self.route.track_points, 2)

    def test_only_managers_load_a_track(self):
        user = self.env['res.users'].create({
            'name': 'Viewer', 'login': 'viewer-gpx',
            'groups_id': [(6, 0, [self.env.ref('bus_tracking.group_bus_user').id])]})
        wizard = self.env['bus.route.gpx'].with_user(user).sudo().create({
            'route_id': self.route.id, 'gpx_file': base64.b64encode(gpx_with(trk(self.LINE)))})
        with self.assertRaises(AccessError):
            wizard.with_user(user).action_load()
