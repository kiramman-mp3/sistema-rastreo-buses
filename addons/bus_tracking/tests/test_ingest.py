from datetime import datetime, timedelta
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import STOPS, BusCase, traccar_position
from .test_driver_auth import make_driver


@tagged('post_install', '-at_install')
class TestIngest(BusCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].set_param('bus_tracking.accept_without_shift', '1')

    def test_position_is_stored_and_speed_converted(self):
        rec = self.bus._apply_position(
            traccar_position(7, '2026-10-26T12:00:00.000+00:00', -33.47, -70.62, speed_knots=10.0))
        self.assertTrue(rec)
        self.assertAlmostEqual(rec.speed, 18.52, places=2)
        self.assertEqual(rec.fix_time, datetime(2026, 10, 26, 12, 0, 0))
        self.assertAlmostEqual(self.bus.last_latitude, -33.47)
        self.assertEqual(self.bus.last_fix_time, datetime(2026, 10, 26, 12, 0, 0))

    def test_timezone_offset_is_normalized_to_utc(self):
        rec = self.bus._apply_position(
            traccar_position(7, '2026-10-26T09:00:00.000-03:00', -33.47, -70.62))
        self.assertEqual(rec.fix_time, datetime(2026, 10, 26, 12, 0, 0))

    def test_duplicate_position_is_ignored(self):
        pos = traccar_position(7, '2026-10-26T12:00:00.000+00:00', -33.47, -70.62)
        self.assertTrue(self.bus._apply_position(pos))
        self.assertFalse(self.bus._apply_position(pos))
        self.assertEqual(self.env['bus.position'].search_count([('vehicle_id', '=', self.bus.id)]), 1)

    def test_invalid_position_is_rejected(self):
        self.assertFalse(self.bus._apply_position({'deviceId': 7, 'latitude': -33.4}))
        self.assertFalse(self.bus._apply_position(
            {'deviceId': 7, 'fixTime': '2026-10-26T12:00:00Z', 'latitude': None, 'longitude': -70.6}))
        self.assertFalse(self.env['bus.position'].search_count([]))

    def test_out_of_range_coordinates_raise_validation_error(self):
        with self.assertRaises(ValidationError):
            self.bus._apply_position(traccar_position(7, '2026-10-26T12:00:00Z', 95.0, -70.62))
        with self.assertRaises(ValidationError):
            self.bus._apply_position(traccar_position(7, '2026-10-26T12:00:00Z', -33.47, 190.0))

    def test_non_numeric_coordinates_raise_validation_error(self):
        with self.assertRaises(ValidationError):
            self.bus._apply_position(traccar_position(7, '2026-10-26T12:00:00Z', 'abc', -70.62))

    def test_invalid_fixtime_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.bus._apply_position(traccar_position(7, 'ayer', -33.47, -70.62))

    def test_position_model_constrains_coordinates(self):
        with self.assertRaises(ValidationError):
            self.env['bus.position'].create({
                'vehicle_id': self.bus.id,
                'fix_time': fields.Datetime.now(),
                'latitude': 95.0,
                'longitude': -70.62,
            })

    def test_older_position_does_not_overwrite_last_state(self):
        self.bus._apply_position(traccar_position(7, '2026-10-26T12:10:00Z', -33.47, -70.62))
        self.bus._apply_position(traccar_position(7, '2026-10-26T12:00:00Z', -33.48, -70.63))
        self.assertAlmostEqual(self.bus.last_latitude, -33.47)
        self.assertEqual(self.bus.last_fix_time, datetime(2026, 10, 26, 12, 10, 0))
        self.assertEqual(self.env['bus.position'].search_count([('vehicle_id', '=', self.bus.id)]), 2)

    def test_arrival_is_logged_once_while_inside_the_radius(self):
        name, lat, lon = STOPS[0]
        self.bus._apply_position(traccar_position(7, '2026-10-26T12:00:00Z', lat, lon))
        self.bus._apply_position(traccar_position(7, '2026-10-26T12:00:10Z', lat + 0.0001, lon))
        arrivals = self.env['bus.stop.arrival'].search([('vehicle_id', '=', self.bus.id)])
        self.assertEqual(len(arrivals), 1)
        self.assertEqual(arrivals.stop_id, self.stop['Terminal'])
        self.assertEqual(self.bus.current_stop_id, self.stop['Terminal'])

    def test_leaving_a_stop_clears_current_stop(self):
        name, lat, lon = STOPS[0]
        self.bus._apply_position(traccar_position(7, '2026-10-26T12:00:00Z', lat, lon))
        self.bus._apply_position(traccar_position(7, '2026-10-26T12:01:00Z', lat - 0.005, lon))
        self.assertFalse(self.bus.current_stop_id)

    def test_full_route_logs_every_stop_in_order(self):
        for minute, (name, lat, lon) in enumerate(STOPS):
            self.bus._apply_position(traccar_position(7, '2026-10-26T12:%02d:00Z' % (minute * 5), lat, lon))
            # a point between stops, so the bus leaves each radius
            self.bus._apply_position(traccar_position(7, '2026-10-26T12:%02d:30Z' % (minute * 5), lat - 0.002, lon + 0.004))
        arrivals = self.env['bus.stop.arrival'].search(
            [('vehicle_id', '=', self.bus.id)], order='arrival_time asc')
        self.assertEqual(arrivals.mapped('stop_id.name'), [s[0] for s in STOPS])

    def test_bus_without_route_never_logs_arrivals(self):
        self.bus.route_id = False
        name, lat, lon = STOPS[0]
        self.bus._apply_position(traccar_position(7, '2026-10-26T12:00:00Z', lat, lon))
        self.assertFalse(self.env['bus.stop.arrival'].search_count([]))

    def test_payload_forwarded_by_traccar_matches_by_device_id(self):
        payload = {
            'position': traccar_position(7, '2026-10-26T12:00:00Z', -33.47, -70.62, speed_knots=5.0),
            'device': {'id': 7, 'uniqueId': 'BUS007'},
        }
        self.assertTrue(self.env['bus.vehicle']._process_traccar_payload(payload))
        self.assertEqual(self.env['bus.position'].search_count([('vehicle_id', '=', self.bus.id)]), 1)

    def test_payload_falls_back_to_unique_id(self):
        payload = {
            'position': {'fixTime': '2026-10-26T12:00:00Z', 'latitude': -33.47, 'longitude': -70.62},
            'device': {'uniqueId': 'BUS007'},
        }
        self.assertTrue(self.env['bus.vehicle']._process_traccar_payload(payload))

    def test_payload_for_unknown_device_is_ignored(self):
        payload = {'position': traccar_position(999, '2026-10-26T12:00:00Z', -33.47, -70.62)}
        self.assertFalse(self.env['bus.vehicle']._process_traccar_payload(payload))
        self.assertFalse(self.env['bus.position'].search_count([]))

    def refresh(self):
        self.bus.invalidate_recordset(['status', 'connected', 'connection'])

    def test_a_bus_that_never_reported_is_disconnected_and_has_no_movement_state(self):
        self.assertEqual((self.bus.connection, self.bus.connected, self.bus.status), ('offline', False, False))

    def test_connected_depends_only_on_the_phone_still_sending(self):
        now = fields.Datetime.now()
        self.bus.write({'last_fix_time': now, 'last_speed': 0.0})
        self.refresh()
        self.assertEqual((self.bus.connection, self.bus.status), ('online', 'stopped'))   # parked but connected
        self.bus.write({'last_speed': 30.0})
        self.refresh()
        self.assertEqual((self.bus.connection, self.bus.status), ('online', 'moving'))

    def test_silence_turns_the_bus_red_but_keeps_its_last_movement_state(self):
        self.bus.write({'last_fix_time': fields.Datetime.now() - timedelta(minutes=4), 'last_speed': 30.0})
        self.refresh()
        self.assertEqual((self.bus.connection, self.bus.connected, self.bus.status), ('offline', False, 'moving'))

    def test_cleanup_deletes_only_positions_older_than_retention(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.retention_days', '30')
        now = fields.Datetime.now()
        Position = self.env['bus.position']
        old = Position.create({'vehicle_id': self.bus.id, 'fix_time': now - timedelta(days=31),
                               'latitude': -33.4, 'longitude': -70.6})
        fresh = Position.create({'vehicle_id': self.bus.id, 'fix_time': now - timedelta(days=1),
                                 'latitude': -33.4, 'longitude': -70.6})
        Position._cron_cleanup()
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())

    def test_cleanup_with_zero_days_keeps_everything(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.retention_days', '0')
        old = self.env['bus.position'].create({
            'vehicle_id': self.bus.id, 'fix_time': fields.Datetime.now() - timedelta(days=400),
            'latitude': -33.4, 'longitude': -70.6})
        self.env['bus.position']._cron_cleanup()
        self.assertTrue(old.exists())

    def test_a_concurrent_duplicate_is_skipped_without_error(self):
        pos = traccar_position(7, '2026-10-26T12:00:00.000+00:00', -33.47, -70.62)
        self.assertTrue(self.bus._apply_position(pos))
        # The other request inserted it between our check and our insert.
        with patch.object(type(self.env['bus.position']), 'search_count', return_value=0):
            self.assertFalse(self.bus._apply_position(pos))
        self.assertEqual(self.env['bus.position'].search_count([('vehicle_id', '=', self.bus.id)]), 1)

    def test_positions_need_an_open_shift(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.accept_without_shift', '0')
        payload = {'position': traccar_position(7, '2026-10-26T12:00:00Z', -33.47, -70.62)}
        self.assertFalse(self.env['bus.vehicle']._process_traccar_payload(payload))
        self.assertFalse(self.env['bus.position'].search_count([]))

        driver = make_driver(self.env, login='chofer_ingesta')
        shift = self.env['bus.shift'].create({
            'user_id': driver.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id})
        self.assertTrue(self.env['bus.vehicle']._process_traccar_payload(payload))

        shift._end()
        later = {'position': traccar_position(7, '2026-10-26T12:01:00Z', -33.47, -70.62)}
        self.assertFalse(self.env['bus.vehicle']._process_traccar_payload(later))
        self.assertEqual(self.env['bus.position'].search_count([]), 1)

    def test_numeric_settings_fall_back_on_typos(self):
        icp = self.env['ir.config_parameter']
        icp.set_param('bus_tracking.speed_limit', 'abc')
        self.assertEqual(self.env['bus.alert']._param('speed_limit', 50), 50)
        icp.set_param('bus_tracking.speed_limit', ' 60 ')
        self.assertEqual(self.env['bus.alert']._param('speed_limit', 50), 60)
        icp.set_param('bus_tracking.retention_days', 'nunca')
        self.env['bus.position']._cron_cleanup()      # must not raise
        icp.set_param('bus_tracking.complaint_retention_days', '9x')
        self.env['bus.complaint']._cron_purge_contacts()

    def test_bus_names_are_unique(self):
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['bus.vehicle'].create({'name': self.bus.name})
            self.env.flush_all()

