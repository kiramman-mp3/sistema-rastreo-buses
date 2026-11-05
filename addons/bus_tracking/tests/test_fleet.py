import importlib.util
from pathlib import Path

from odoo.tests import TransactionCase, tagged
from psycopg2 import IntegrityError
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestFleetLink(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Bus = self.env['bus.vehicle']
        self.Fleet = self.env['fleet.vehicle']
        self.driver = self.env['res.partner'].create({'name': 'Chofer Uno'})
        self.other_driver = self.env['res.partner'].create({'name': 'Chofer Dos'})
        self.bus = self.Bus.create({'name': 'Bus 1', 'plate': 'TBA-1234', 'capacity': 40, 'driver_id': self.driver.id})

    # ------------------------------------------------------------------ creating
    def test_creating_a_bus_creates_its_vehicle_in_fleet(self):
        vehicle = self.bus.fleet_vehicle_id
        self.assertTrue(vehicle)
        self.assertEqual((vehicle.license_plate, vehicle.seats, vehicle.driver_id), ('TBA-1234', 40, self.driver))
        self.assertEqual((vehicle.model_id.brand_id.name, vehicle.model_id.name), ('UTA', 'Bus'))

    def test_two_buses_have_two_vehicles(self):
        other = self.Bus.create({'name': 'Bus 2', 'plate': 'TBA-5678'})
        self.assertNotEqual(self.bus.fleet_vehicle_id, other.fleet_vehicle_id)
        self.assertEqual(other.fleet_vehicle_id.license_plate, 'TBA-5678')

    def test_a_bus_without_plate_still_gets_a_vehicle(self):
        bus = self.Bus.create({'name': 'Bus sin placa'})
        self.assertTrue(bus.fleet_vehicle_id)
        self.assertFalse(bus.fleet_vehicle_id.license_plate)

    def test_a_simulated_bus_never_reaches_fleet(self):
        before = self.Fleet.search_count([])
        bus = self.Bus.create({'name': 'Sim X', 'simulated': True, 'plate': 'SIM-1'})
        self.assertFalse(bus.fleet_vehicle_id)
        self.assertEqual(self.Fleet.search_count([]), before)

    def test_a_vehicle_belongs_to_one_bus_only(self):
        other = self.Bus.create({'name': 'Bus 2', 'plate': 'TBA-5678'})
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            other.fleet_vehicle_id = self.bus.fleet_vehicle_id

    # ------------------------------------------------------------------ the bus changes
    def test_editing_the_plate_of_the_bus_updates_fleet(self):
        self.bus.plate = 'TBA-9999'
        self.assertEqual(self.bus.fleet_vehicle_id.license_plate, 'TBA-9999')

    def test_editing_the_driver_and_the_seats_of_the_bus_updates_fleet(self):
        self.bus.write({'driver_id': self.other_driver.id, 'capacity': 52})
        vehicle = self.bus.fleet_vehicle_id
        self.assertEqual((vehicle.driver_id, vehicle.seats), (self.other_driver, 52))

    def test_archiving_the_bus_archives_the_vehicle(self):
        self.bus.active = False
        self.assertFalse(self.bus.fleet_vehicle_id.active)
        self.bus.active = True
        self.assertTrue(self.bus.fleet_vehicle_id.active)

    def test_what_the_bus_does_not_share_is_left_alone(self):
        self.bus.fleet_vehicle_id.color = 'Blue'
        self.bus.write({'name': 'Bus uno', 'route_id': False})
        self.assertEqual(self.bus.fleet_vehicle_id.color, 'Blue')

    # ------------------------------------------------------------------ fleet changes
    def test_editing_the_plate_in_fleet_updates_the_bus(self):
        self.bus.fleet_vehicle_id.license_plate = 'TBA-0001'
        self.assertEqual(self.bus.plate, 'TBA-0001')

    def test_editing_the_driver_and_the_seats_in_fleet_updates_the_bus(self):
        self.bus.fleet_vehicle_id.write({'driver_id': self.other_driver.id, 'seats': 30})
        self.assertEqual((self.bus.driver_id, self.bus.capacity), (self.other_driver, 30))

    def test_archiving_the_vehicle_in_fleet_archives_the_bus(self):
        self.bus.fleet_vehicle_id.active = False
        self.assertFalse(self.bus.active)

    def test_the_two_sides_do_not_bounce_changes_back(self):
        """A change in one side is copied once: the plate that was typed stays as it was typed."""
        self.bus.plate = ' tba-77 '
        self.assertEqual(self.bus.plate, ' tba-77 ')
        self.bus.fleet_vehicle_id.license_plate = 'TBA-88'
        self.assertEqual(self.bus.plate, 'TBA-88')
        self.assertEqual(self.bus.fleet_vehicle_id.license_plate, 'TBA-88')

    def test_a_vehicle_that_is_not_a_bus_is_left_alone(self):
        car = self.Fleet.create({'model_id': self.env.ref('bus_tracking.fleet_model_bus').id,
                                 'license_plate': 'CAR-1'})
        car.license_plate = 'CAR-2'
        self.assertFalse(car.bus_id)
        self.assertEqual(self.bus.plate, 'TBA-1234')

    def test_deleting_the_vehicle_keeps_the_bus(self):
        bus = self.Bus.create({'name': 'Bus sin chofer', 'plate': 'DEL-1'})        # Fleet keeps a vehicle with a driver
        bus.fleet_vehicle_id.unlink()
        self.assertTrue(bus.exists())
        self.assertFalse(bus.fleet_vehicle_id)

    # ------------------------------------------------------------------ linking the existing buses
    def test_linking_the_existing_buses_gives_each_its_vehicle_without_duplicates(self):
        old = self.Bus.create({'name': 'Bus viejo', 'plate': 'OLD-1'})
        old.fleet_vehicle_id.unlink()                      # a bus that was registered before Fleet joined
        self.assertFalse(old.fleet_vehicle_id)
        count = self.Fleet.search_count([])
        self.assertEqual(self.Bus.search([])._link_fleet(), old)
        self.assertEqual(self.Fleet.search_count([]), count + 1)
        self.assertEqual(old.fleet_vehicle_id.license_plate, 'OLD-1')
        self.assertEqual(self.Bus.search([])._link_fleet(), self.Bus)          # again: nothing to do
        self.assertEqual(self.Fleet.search_count([]), count + 1)

    def test_a_vehicle_that_already_has_the_plate_is_linked_not_duplicated(self):
        existing = self.Fleet.create({'model_id': self.env.ref('bus_tracking.fleet_model_bus').id,
                                      'license_plate': 'PRE-1'})
        count = self.Fleet.search_count([])
        bus = self.Bus.create({'name': 'Bus con placa', 'plate': 'PRE-1'})
        self.assertEqual(bus.fleet_vehicle_id, existing)
        self.assertEqual(self.Fleet.search_count([]), count)

    def test_the_migration_links_the_buses_that_were_already_there(self):
        old = self.Bus.create({'name': 'Bus viejo', 'plate': 'OLD-2'})
        old.fleet_vehicle_id.unlink()
        path = Path(__file__).resolve().parents[1] / 'migrations' / '16.0.1.6.0' / 'post-migrate.py'
        spec = importlib.util.spec_from_file_location('post_migrate_fleet', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, '16.0.1.5.0')
        self.assertTrue(self.Bus.browse(old.id).fleet_vehicle_id)

    # ------------------------------------------------------------------ screens
    def test_the_bus_opens_its_vehicle_in_fleet(self):
        action = self.bus.action_open_fleet()
        self.assertEqual((action['res_model'], action['res_id']), ('fleet.vehicle', self.bus.fleet_vehicle_id.id))

    def test_the_vehicle_shows_the_gps_device_of_its_bus(self):
        self.bus.traccar_device_id = 4711
        vehicle = self.bus.fleet_vehicle_id
        self.assertEqual(vehicle.bus_id, self.bus)
        self.assertEqual(vehicle.bus_traccar_device_id, 4711)
        self.assertEqual(vehicle.action_open_bus()['res_id'], self.bus.id)

    def test_a_manager_can_open_the_fleet_menu_and_the_buses_stay_in_the_bus_menu(self):
        manager = self.env['res.users'].create({
            'name': 'Gestor', 'login': 'fleet-manager',
            'groups_id': [(6, 0, [self.env.ref('bus_tracking.group_bus_manager').id])]})
        self.assertTrue(manager.has_group('fleet.fleet_group_manager'))
        menu = self.env.ref('bus_tracking.menu_bus_fleet_vehicles')
        self.assertEqual(menu.action.res_model, 'fleet.vehicle')
        self.assertIn(menu.id, self.env['ir.ui.menu'].with_user(manager)._visible_menu_ids())
        self.assertEqual(self.env.ref('bus_tracking.menu_bus_vehicle').parent_id,
                         self.env.ref('bus_tracking.menu_bus_fleet'))
        self.assertEqual(len(self.Fleet.with_user(manager).search([('id', '=', self.bus.fleet_vehicle_id.id)])), 1)

    def test_a_bus_user_who_is_not_a_manager_does_not_get_the_fleet_menu(self):
        viewer = self.env['res.users'].create({
            'name': 'Lector', 'login': 'fleet-viewer',
            'groups_id': [(6, 0, [self.env.ref('bus_tracking.group_bus_user').id])]})
        self.assertFalse(viewer.has_group('fleet.fleet_group_user'))
        menu = self.env.ref('bus_tracking.menu_bus_fleet_vehicles')
        self.assertEqual(menu.groups_id, self.env.ref('bus_tracking.group_bus_manager'))
