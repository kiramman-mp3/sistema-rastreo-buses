import base64
import logging
import math
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from psycopg2 import IntegrityError

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger

from .utils import KNOTS_TO_KMH, MOVING_ABOVE_KMH, haversine_m, parse_traccar_dt

_logger = logging.getLogger(__name__)

CONNECTED_WITHIN = timedelta(minutes=3)     # the phone sends every few seconds while the app is open


class BusVehicle(models.Model):
    _name = 'bus.vehicle'
    _description = 'Bus'
    _order = 'name'

    name = fields.Char(required=True)
    plate = fields.Char()
    capacity = fields.Integer()
    active = fields.Boolean(default=True)
    driver_id = fields.Many2one('res.partner', string="Driver")
    route_id = fields.Many2one('bus.route', string="Route")
    traccar_device_id = fields.Integer(string="Traccar Device ID", copy=False)
    # In the OsmAnd protocol the identifier is the only credential: only managers may read it.
    traccar_unique_id = fields.Char(string="Traccar Unique ID", copy=False,
                                    groups='bus_tracking.group_bus_manager')

    tablet_setup_link = fields.Char(string="Tablet setup link", compute='_compute_tablet_setup',
                                    groups='bus_tracking.group_bus_manager')
    tablet_qr = fields.Binary(string="Tablet QR", compute='_compute_tablet_setup',
                              groups='bus_tracking.group_bus_manager')

    last_latitude = fields.Float(digits=(10, 7), readonly=True, copy=False)
    last_longitude = fields.Float(digits=(10, 7), readonly=True, copy=False)
    last_speed = fields.Float(readonly=True, copy=False)
    last_course = fields.Float(readonly=True, copy=False)
    last_fix_time = fields.Datetime(readonly=True, copy=False)
    current_stop_id = fields.Many2one('bus.route.stop', readonly=True, copy=False)
    off_route_since = fields.Datetime(readonly=True, copy=False)
    connection = fields.Selection(
        [('online', "🟢 Conectado"), ('offline', "🔴 Sin conexión")], string="Connection",
        compute='_compute_status', help="Green while the phone keeps sending its position, even if the bus is parked.")
    connected = fields.Boolean(compute='_compute_status')
    status = fields.Selection(
        [('moving', "En movimiento"), ('stopped', "Parado")], compute='_compute_status',
        help="From the last speed reported.")

    _sql_constraints = [
        ('traccar_device_uniq', 'unique(traccar_device_id)', "Traccar device is already linked to another bus."),
    ]

    @api.model
    def _tablet_setup_pair(self):
        """QR the Buses UTA app scans: only the public Odoo URL, never the Traccar id."""
        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        if base.endswith('/web'):
            base = base[:-4].rstrip('/')
        if not base:
            return False, False
        link = 'uta-buses://setup?' + urlencode({'odoo': base})
        png = self.env['ir.actions.report'].barcode('QR', link, width=260, height=260)
        return link, base64.b64encode(png)

    @api.depends()
    def _compute_tablet_setup(self):
        link, qr = self._tablet_setup_pair()
        for bus in self:
            bus.tablet_setup_link = link
            bus.tablet_qr = qr

    @api.depends('last_fix_time', 'last_speed')
    def _compute_status(self):
        now = fields.Datetime.now()
        for bus in self:
            bus.connected = bool(bus.last_fix_time and now - bus.last_fix_time <= CONNECTED_WITHIN)
            bus.connection = 'online' if bus.connected else 'offline'
            if bus.last_fix_time:
                bus.status = 'moving' if bus.last_speed > MOVING_ABOVE_KMH else 'stopped'
            else:
                bus.status = False

    # ------------------------------------------------------------------
    # Position ingestion
    # ------------------------------------------------------------------
    def _apply_position(self, pos):
        """Store a Traccar position dict and refresh the bus state."""
        self.ensure_one()
        raw_time = pos.get('fixTime')
        if not raw_time:
            return False
        fix_time = parse_traccar_dt(raw_time)
        if not fix_time:
            raise ValidationError(_("Invalid fixTime format."))
        lat_raw = pos.get('latitude')
        lon_raw = pos.get('longitude')
        if lat_raw is None or lon_raw is None:
            return False
        try:
            lat = float(lat_raw)
            lon = float(lon_raw)
        except (ValueError, TypeError):
            raise ValidationError(_("Latitude and longitude must be numbers."))
        if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
            raise ValidationError(_("Latitude and longitude must be finite numbers."))
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValidationError(_("Latitude must be between -90 and 90, and longitude between -180 and 180."))
        if self.env['bus.position'].search_count(
                [('vehicle_id', '=', self.id), ('fix_time', '=', fix_time)]):
            return False
        speed_raw = pos.get('speed')
        try:
            speed = (float(speed_raw) if speed_raw is not None else 0.0) * KNOTS_TO_KMH
        except (ValueError, TypeError):
            speed = 0.0
        course_raw = pos.get('course')
        try:
            course = float(course_raw) if course_raw is not None else 0.0
        except (ValueError, TypeError):
            course = 0.0
        alt_raw = pos.get('altitude')
        try:
            altitude = float(alt_raw) if alt_raw is not None else 0.0
        except (ValueError, TypeError):
            altitude = 0.0
        try:
            # The webhook and the cron can bring the same fix at once: the unique constraint
            # decides, and the loser just skips it instead of failing the whole request.
            with self.env.cr.savepoint(), mute_logger('odoo.sql_db'):
                record = self.env['bus.position'].create({
                    'vehicle_id': self.id,
                    'fix_time': fix_time,
                    'latitude': lat,
                    'longitude': lon,
                    'speed': speed,
                    'course': course,
                    'altitude': altitude,
                    'address': pos.get('address'),
                })
        except IntegrityError:
            return False
        if not self.last_fix_time or fix_time >= self.last_fix_time:
            self.write({
                'last_latitude': lat,
                'last_longitude': lon,
                'last_speed': speed,
                'last_course': course,
                'last_fix_time': fix_time,
            })
            self._update_current_stop(lat, lon, fix_time)
            self.env['bus.alert']._on_position(self, speed, fix_time)
        return record

    def _update_current_stop(self, lat, lon, when):
        """Log an arrival when the bus enters a stop radius of its route."""
        self.ensure_one()
        previous = self.current_stop_id
        nearest, nearest_dist = False, None
        for stop in self.route_id.stop_ids:
            dist = haversine_m(lat, lon, stop.latitude, stop.longitude)
            if dist <= stop.radius and (nearest_dist is None or dist < nearest_dist):
                nearest, nearest_dist = stop, dist
        if nearest and nearest != self.current_stop_id:
            self.env['bus.stop.arrival'].create({
                'vehicle_id': self.id,
                'stop_id': nearest.id,
                'arrival_time': when,
            })
        if nearest != self.current_stop_id:
            self.current_stop_id = nearest
            self.env['bus.run']._on_stop_change(self, previous, nearest or self.env['bus.route.stop'], when)

    @api.model
    def _process_traccar_payload(self, payload):
        """Handle a body forwarded by Traccar (forward.json=true)."""
        pos = payload.get('position') or payload
        device = payload.get('device') or {}
        domain = []
        if pos.get('deviceId') or device.get('id'):
            domain = [('traccar_device_id', '=', pos.get('deviceId') or device.get('id'))]
        elif device.get('uniqueId'):
            domain = [('traccar_unique_id', '=', device['uniqueId'])]
        if not domain:
            return False
        vehicle = self.search(domain, limit=1)
        if not vehicle or not vehicle._accepts_positions():
            return False
        return vehicle._apply_position(pos)

    def _accepts_positions(self):
        """A bus only reports while a driver has it on a shift: a tablet left on after the shift
        closed must not keep drawing it on the map. A setting allows them for tests with curl."""
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param('bus_tracking.accept_without_shift') in ('1', 'True', 'true'):
            return True
        return bool(self.env['bus.shift'].sudo().search_count(
            [('vehicle_id', '=', self.id), ('state', '=', 'active')]))

    # ------------------------------------------------------------------
    # Pull sync
    # ------------------------------------------------------------------
    def _sync_from_traccar(self):
        positions = self.env['bus.traccar.api'].get_latest_positions()
        by_device = {p['deviceId']: p for p in positions if p.get('deviceId')}
        for bus in self.filtered('traccar_device_id'):
            pos = by_device.get(bus.traccar_device_id)
            if pos and bus._accepts_positions():
                try:
                    bus._apply_position(pos)
                except ValidationError:
                    _logger.warning("Ignoring invalid position from Traccar for bus %s", bus.name)

    @api.model
    def _cron_sync_positions(self):
        if not self.env['bus.traccar.api'].is_configured():
            return
        buses = self.search([('traccar_device_id', '!=', False)])
        try:
            buses._sync_from_traccar()
        except UserError as e:
            _logger.warning("Traccar sync failed: %s", e.args[0])

    def action_register_gps(self):
        """Create the phone's device in Traccar with a random identifier."""
        api = self.env['bus.traccar.api']
        for bus in self:
            if bus.traccar_device_id:
                raise UserError(_("%s already has a GPS device.", bus.name))
            unique_id = 'b-' + secrets.token_hex(8)
            device = api.create_device(bus.name, unique_id)
            bus.write({'traccar_device_id': device['id'], 'traccar_unique_id': unique_id})

    def action_sync_now(self):
        self._sync_from_traccar()

    def action_open_map(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'bus_tracking.live_map',
            'name': _("Live Map"),
            'params': {'vehicle_id': self.id},
        }
