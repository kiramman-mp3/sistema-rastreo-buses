import base64
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .utils import KNOTS_TO_KMH, MOVING_ABOVE_KMH, haversine_m, parse_traccar_dt

_logger = logging.getLogger(__name__)

OFFLINE_AFTER = timedelta(minutes=5)


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

    gps_setup_link = fields.Char(string="Phone setup link", compute='_compute_gps_setup',
                                 groups='bus_tracking.group_bus_manager')
    gps_qr = fields.Binary(string="Phone setup QR", compute='_compute_gps_setup',
                           groups='bus_tracking.group_bus_manager')

    last_latitude = fields.Float(digits=(10, 7), readonly=True, copy=False)
    last_longitude = fields.Float(digits=(10, 7), readonly=True, copy=False)
    last_speed = fields.Float(readonly=True, copy=False)
    last_course = fields.Float(readonly=True, copy=False)
    last_fix_time = fields.Datetime(readonly=True, copy=False)
    current_stop_id = fields.Many2one('bus.route.stop', readonly=True, copy=False)
    off_route_since = fields.Datetime(readonly=True, copy=False)
    status = fields.Selection(
        [('moving', "Moving"), ('stopped', "Stopped"), ('offline', "Offline")],
        compute='_compute_status')

    _sql_constraints = [
        ('traccar_device_uniq', 'unique(traccar_device_id)', "Traccar device is already linked to another bus."),
    ]

    @api.depends('traccar_unique_id')
    def _compute_gps_setup(self):
        """Link and QR for the Traccar Client app. The app documents the server URL and the
        device identifier; the link format is not officially documented, so the QR is a
        convenience and the values must also be usable by typing them in."""
        base = (self.env['ir.config_parameter'].sudo().get_param('bus_tracking.gps_url') or '').rstrip('/')
        for bus in self:
            if bus.traccar_unique_id and base:
                link = 'org.traccar.client://config?' + urlencode(
                    {'url': base, 'id': bus.traccar_unique_id, 'interval': 10, 'distance': 0})
                bus.gps_setup_link = link
                bus.gps_qr = base64.b64encode(
                    self.env['ir.actions.report'].barcode('QR', link, width=260, height=260))
            else:
                bus.gps_setup_link = False
                bus.gps_qr = False

    @api.depends('last_fix_time', 'last_speed')
    def _compute_status(self):
        now = fields.Datetime.now()
        for bus in self:
            if not bus.last_fix_time or now - bus.last_fix_time > OFFLINE_AFTER:
                bus.status = 'offline'
            else:
                bus.status = 'moving' if bus.last_speed > MOVING_ABOVE_KMH else 'stopped'

    # ------------------------------------------------------------------
    # Position ingestion
    # ------------------------------------------------------------------
    def _apply_position(self, pos):
        """Store a Traccar position dict and refresh the bus state."""
        self.ensure_one()
        fix_time = parse_traccar_dt(pos.get('fixTime'))
        if not fix_time or pos.get('latitude') is None or pos.get('longitude') is None:
            return False
        if self.env['bus.position'].search_count(
                [('vehicle_id', '=', self.id), ('fix_time', '=', fix_time)]):
            return False
        speed = (pos.get('speed') or 0.0) * KNOTS_TO_KMH
        record = self.env['bus.position'].create({
            'vehicle_id': self.id,
            'fix_time': fix_time,
            'latitude': pos['latitude'],
            'longitude': pos['longitude'],
            'speed': speed,
            'course': pos.get('course') or 0.0,
            'altitude': pos.get('altitude') or 0.0,
            'address': pos.get('address'),
        })
        if not self.last_fix_time or fix_time >= self.last_fix_time:
            self.write({
                'last_latitude': pos['latitude'],
                'last_longitude': pos['longitude'],
                'last_speed': speed,
                'last_course': pos.get('course') or 0.0,
                'last_fix_time': fix_time,
            })
            self._update_current_stop(pos['latitude'], pos['longitude'], fix_time)
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
        return vehicle._apply_position(pos) if vehicle else False

    # ------------------------------------------------------------------
    # Pull sync
    # ------------------------------------------------------------------
    def _sync_from_traccar(self):
        positions = self.env['bus.traccar.api'].get_latest_positions()
        by_device = {p['deviceId']: p for p in positions if p.get('deviceId')}
        for bus in self.filtered('traccar_device_id'):
            pos = by_device.get(bus.traccar_device_id)
            if pos:
                bus._apply_position(pos)

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
