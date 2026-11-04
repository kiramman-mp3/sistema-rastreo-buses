"""What the system measures about itself: the positions it refused, whether Odoo agrees with Traccar, and how
long its queries take. They feed the software-quality indicators (S1 to S3) of `bus.kpi`."""
import logging
import time
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .utils import parse_traccar_dt

_logger = logging.getLogger(__name__)

SAME_PLACE_DEG = 1e-5          # about a metre: a position that differs less is the same position
PERF_KEEP_DAYS = 90


class BusPositionReject(models.Model):
    _name = 'bus.position.reject'
    _description = 'Rejected GPS position'
    _order = 'create_date desc, id desc'

    vehicle_id = fields.Many2one('bus.vehicle', ondelete='set null', index=True)
    device_id = fields.Integer()
    reason = fields.Char()

    @api.model
    def _log(self, payload, reason):
        """Remember that a position was refused (invalid coordinates or time), without keeping its content."""
        payload = payload if isinstance(payload, dict) else {}
        pos = payload.get('position') if isinstance(payload.get('position'), dict) else payload
        info = payload.get('device') if isinstance(payload.get('device'), dict) else {}
        device = pos.get('deviceId') or info.get('id')
        try:
            device = int(device) if device else 0
        except (TypeError, ValueError):
            device = 0
        vehicle = self.env['bus.vehicle'].sudo()
        vehicle = vehicle.search([('traccar_device_id', '=', device)], limit=1) if device else vehicle
        return self.sudo().create({
            'vehicle_id': vehicle.id if vehicle else False, 'device_id': device, 'reason': (reason or '')[:200]})


class BusSyncAudit(models.Model):
    _name = 'bus.sync.audit'
    _description = 'Traccar to Odoo synchronisation audit'
    _order = 'run_at desc, id desc'

    run_at = fields.Datetime(default=fields.Datetime.now, index=True)
    vehicle_id = fields.Many2one('bus.vehicle', ondelete='cascade', index=True)
    since = fields.Datetime()
    until = fields.Datetime()
    total = fields.Integer(help="Positions Traccar has that Odoo should have kept.")
    matched = fields.Integer(help="The same position (device, time, place) is in Odoo.")
    missing = fields.Integer(help="In Traccar but not in Odoo.")
    mismatched = fields.Integer(help="In both, with a different place.")
    accuracy = fields.Float(compute='_compute_accuracy', store=True, string="Accuracy (%)")

    @api.depends('total', 'matched')
    def _compute_accuracy(self):
        for audit in self:
            audit.accuracy = 100.0 * audit.matched / audit.total if audit.total else 0.0

    @api.model
    def _run(self, hours=6):
        """Compare the positions Traccar holds for each bus with the ones Odoo kept, for the last hours.
        A position of a bus with no shift is not counted: Odoo drops those on purpose."""
        api_client = self.env['bus.traccar.api']
        if not api_client.is_configured():
            raise UserError(_("Traccar URL is not configured."))
        until = fields.Datetime.now()
        since = until - timedelta(hours=hours)
        audits = self
        for bus in self.env['bus.vehicle'].search([('traccar_device_id', '!=', False), ('simulated', '=', False)]):
            theirs = api_client.get_positions(bus.traccar_device_id, since, until)
            total = matched = missing = mismatched = 0
            for pos in theirs:
                when = parse_traccar_dt(pos.get('fixTime'))
                if not when or not bus._expects_position(when):
                    continue
                total += 1
                mine = self.env['bus.position'].search([('vehicle_id', '=', bus.id), ('fix_time', '=', when)], limit=1)
                if not mine:
                    missing += 1
                elif (abs(mine.latitude - float(pos.get('latitude', 0))) > SAME_PLACE_DEG
                      or abs(mine.longitude - float(pos.get('longitude', 0))) > SAME_PLACE_DEG):
                    mismatched += 1
                else:
                    matched += 1
            if total:
                audits |= self.create({
                    'vehicle_id': bus.id, 'since': since, 'until': until, 'total': total,
                    'matched': matched, 'missing': missing, 'mismatched': mismatched})
        return audits

    @api.model
    def _cron_run(self):
        if self.env['bus.traccar.api'].is_configured():
            try:
                self._run()
            except UserError as error:
                _logger.warning("Synchronisation audit failed: %s", error.args[0])


class BusPerfSample(models.Model):
    _name = 'bus.perf.sample'
    _description = 'Response time sample'
    _order = 'created desc, id desc'

    name = fields.Char(required=True, index=True)
    ms = fields.Float(string="Milliseconds")
    rows = fields.Integer()
    created = fields.Datetime(default=fields.Datetime.now, index=True)

    @api.model
    def _measure(self):
        """Time the queries behind the map, the history of a bus, the trip list and the indicators."""
        Vehicle, Position, Trip = self.env['bus.vehicle'], self.env['bus.position'], self.env['bus.trip']
        since = fields.Datetime.now() - timedelta(hours=4)
        bus = Position.search([('fix_time', '>=', since)], limit=1).vehicle_id

        def live():
            return Vehicle.search_read([('last_fix_time', '!=', False), ('simulated', '=', False)],
                                       ['name', 'last_latitude', 'last_longitude', 'last_speed', 'last_fix_time'])

        def history():
            return Position.search_read([('vehicle_id', '=', bus.id), ('fix_time', '>=', since)],
                                        ['latitude', 'longitude'], order='fix_time asc', limit=5000) if bus else []

        def trips():
            return Trip.search_read([], ['name', 'state', 'planned_start', 'delay_end_min'], limit=200)

        def indicators():
            return self.env['bus.kpi'].compute()['metrics']

        samples = self
        for name, work in (('live', live), ('history', history), ('trips', trips), ('indicators', indicators)):
            started = time.perf_counter()
            rows = len(work())
            samples |= self.create({'name': name, 'ms': (time.perf_counter() - started) * 1000.0, 'rows': rows})
        self.search([('created', '<', fields.Datetime.now() - timedelta(days=PERF_KEEP_DAYS))]).unlink()
        return samples

    @api.model
    def _cron_measure(self):
        self._measure()
