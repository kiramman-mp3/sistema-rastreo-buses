from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import BusCase


@tagged('post_install', '-at_install')
class TestStopPicker(BusCase):

    def save(self, stop_id=False, **vals):
        values = dict(name='Nueva', latitude=-1.25, longitude=-78.62, radius=60)
        values.update(vals)
        return self.env['bus.route.stop']._save_from_map(self.route.id, stop_id, **values)

    def test_buttons_open_the_map_with_the_route_and_the_stop(self):
        action = self.route.action_add_stop_on_map()
        self.assertEqual((action['tag'], action['params']),
                         ('bus_tracking.stop_picker', {'route_id': self.route.id, 'stop_id': False}))
        stop = self.stop['Plaza']
        self.assertEqual(stop.action_pick_on_map()['params'], {'route_id': self.route.id, 'stop_id': stop.id})

    def test_a_new_stop_goes_to_the_end_of_the_route(self):
        stop = self.save()
        self.assertEqual(self.route.stop_ids[-1], stop)
        self.assertGreater(stop.sequence, self.stop['Hospital'].sequence)
        self.assertAlmostEqual(stop.latitude, -1.25, places=6)
        self.assertAlmostEqual(stop.longitude, -78.62, places=6)
        self.assertEqual(stop.radius, 60)

    def test_an_existing_stop_is_moved_and_renamed(self):
        plaza = self.stop['Plaza']
        self.save(plaza.id, name='Plaza grande', latitude=-33.4541)
        self.assertEqual((plaza.name, plaza.latitude, plaza.sequence), ('Plaza grande', -33.4541, 20))
        self.assertEqual(len(self.route.stop_ids), 3)

    def test_a_stop_of_another_route_cannot_be_changed(self):
        other = self.env['bus.route'].create({'name': 'Otra', 'code': 'O1'})
        foreign = self.env['bus.route.stop'].create(
            {'route_id': other.id, 'name': 'Ajena', 'latitude': 0, 'longitude': 0})
        with self.assertRaises(UserError):
            self.save(foreign.id)

    def test_bad_values_are_refused(self):
        for bad in (dict(name='  '), dict(latitude=95), dict(longitude=-181), dict(radius=2), dict(radius=5000),
                    dict(latitude=None)):
            with self.assertRaises(UserError, msg=str(bad)):
                self.save(**bad)

    def test_only_managers_can_edit_stops(self):
        viewer = self.env['res.users'].create({
            'name': 'Lector', 'login': 'lector@example.org',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id,
                                  self.env.ref('bus_tracking.group_bus_user').id])]})
        with self.assertRaises(AccessError):
            self.env['bus.route.stop'].with_user(viewer)._save_from_map(self.route.id, False, 'X', 0, 0, 50)

    def test_the_model_refuses_impossible_stops(self):
        Stop = self.env['bus.route.stop']
        base = {'route_id': self.route.id, 'name': 'X', 'latitude': -1.2, 'longitude': -78.6}
        for wrong in ({'latitude': 95}, {'longitude': -190}, {'radius': 0}, {'radius': 5000}):
            with self.assertRaises(ValidationError, msg=wrong):
                Stop.create(dict(base, **wrong))
        self.assertTrue(Stop.create(dict(base, radius=40)))

    def test_route_colour_must_be_hex(self):
        with self.assertRaises(ValidationError):
            self.route.color = 'red'
        self.route.color = '#AA00ff'
        self.route.color = False

    def test_the_measured_line_follows_stop_edits(self):
        first = self.route._path_measure()
        self.assertIs(self.route._path_measure(), first)
        # An edit made later, in another request, changes the stop's write date.
        self.stop['Plaza'].latitude = -33.47
        self.env.flush_all()
        self.env.cr.execute("UPDATE bus_route_stop SET write_date = write_date + interval '1 minute' WHERE id = %s",
                            [self.stop['Plaza'].id])
        self.stop['Plaza'].invalidate_recordset(['write_date'])
        self.assertIsNot(self.route._path_measure(), first)
