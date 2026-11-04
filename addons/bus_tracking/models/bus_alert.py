from datetime import timedelta

from odoo import _, api, fields, models

from .utils import MOVING_ABOVE_KMH, int_param

KINDS = [
    ('speeding', "Speeding"),
    ('offline', "No signal"),
    ('long_stop', "Long stop"),
    ('off_route', "Off route"),
]

# A bus that never reported in this long is parked for the night, not "without signal".
RECENTLY_ACTIVE = timedelta(hours=6)


class BusAlert(models.Model):
    _name = 'bus.alert'
    _description = 'Bus Alert'
    _order = 'start_time desc, id desc'

    vehicle_id = fields.Many2one('bus.vehicle', required=True, ondelete='cascade', index=True)
    route_id = fields.Many2one('bus.route', ondelete='set null')
    kind = fields.Selection(KINDS, required=True, index=True)
    state = fields.Selection([('open', "Open"), ('closed', "Closed")], required=True, default='open', index=True)
    start_time = fields.Datetime(required=True)
    end_time = fields.Datetime()
    duration_minutes = fields.Float(compute='_compute_duration')
    max_speed = fields.Float(help="km/h")
    threshold = fields.Float(help="Limit that was exceeded when the alert opened (km/h or minutes).")
    distance_m = fields.Float(help="How far from the road the bus got (metres).")
    notified = fields.Boolean(default=False, index=True)
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    detail = fields.Char(compute='_compute_detail')
    trip_id = fields.Many2one('bus.trip', string="Trip", ondelete='set null', index=True)

    def init(self):
        # One open alert per bus and kind, enforced by the database.
        self.env.cr.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS bus_alert_one_open_idx "
            "ON bus_alert (vehicle_id, kind) WHERE state = 'open'")

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        now = fields.Datetime.now()
        for alert in self:
            if alert.start_time:
                end = alert.end_time or now
                alert.duration_minutes = max((end - alert.start_time).total_seconds() / 60.0, 0.0)
            else:
                alert.duration_minutes = 0.0

    @api.depends('kind', 'max_speed', 'threshold', 'duration_minutes', 'distance_m')
    @api.depends_context('lang')
    def _compute_detail(self):
        for alert in self:
            if alert.kind == 'speeding':
                alert.detail = _("Up to %(speed)d km/h (limit %(limit)d km/h)",
                                 speed=round(alert.max_speed), limit=round(alert.threshold))
            elif alert.kind == 'offline':
                alert.detail = _("No reports for %(minutes)d min", minutes=round(alert.duration_minutes))
            elif alert.kind == 'long_stop':
                alert.detail = _("Stopped for %(minutes)d min away from any stop",
                                 minutes=round(alert.duration_minutes))
            elif alert.kind == 'off_route':
                alert.detail = _("Up to %(meters)d m away from its route (limit %(limit)d m)",
                                 meters=round(alert.distance_m), limit=round(alert.threshold))
            else:
                alert.detail = False

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------
    @api.model
    def _param(self, key, default):
        return int_param(self.env, 'bus_tracking.' + key, default)

    @api.model
    def _open_alert(self, vehicle, kind, start_time, **vals):
        """Open an alert unless one is already open for this bus and kind."""
        existing = self.search([('vehicle_id', '=', vehicle.id), ('kind', '=', kind), ('state', '=', 'open')], limit=1)
        if existing:
            return existing
        alert = self.create(dict(
            vals,
            vehicle_id=vehicle.id,
            route_id=vehicle.route_id.id,
            trip_id=self.env['bus.trip']._trip_at(vehicle, start_time).id,
            kind=kind,
            start_time=start_time,
            latitude=vehicle.last_latitude,
            longitude=vehicle.last_longitude,
        ))
        return alert

    def _close(self, end_time):
        self.filtered(lambda a: a.state == 'open').write({'state': 'closed', 'end_time': end_time})

    @api.model
    def _on_position(self, vehicle, speed, fix_time):
        """Evaluate the per-position rules after the bus state was refreshed."""
        open_by_kind = {a.kind: a for a in self.search([('vehicle_id', '=', vehicle.id), ('state', '=', 'open')])}
        # Any new report ends a silence, and moving ends a long stop.
        if 'offline' in open_by_kind:
            open_by_kind['offline']._close(fix_time)
        if speed > MOVING_ABOVE_KMH and 'long_stop' in open_by_kind:
            open_by_kind['long_stop']._close(fix_time)

        limit = self._param('speed_limit', 50)
        speeding = open_by_kind.get('speeding')
        if limit > 0 and speed > limit:
            if speeding:
                if speed > speeding.max_speed:
                    speeding.max_speed = speed
            else:
                self._open_alert(vehicle, 'speeding', fix_time, max_speed=speed, threshold=limit)
        elif speeding:
            speeding._close(fix_time)

        self._check_off_route(vehicle, fix_time, open_by_kind.get('off_route'))

    @api.model
    def _check_off_route(self, vehicle, fix_time, open_alert):
        """Alert when a bus stays away from the line that joins the stops of its route."""
        limit = self._param('off_route_meters', 150)
        measure = vehicle.route_id._path_measure() if limit > 0 and vehicle.route_id else None
        if not measure or vehicle.current_stop_id:
            if vehicle.off_route_since:
                vehicle.off_route_since = False
            if open_alert:
                open_alert._close(fix_time)
            return
        _along, offset = measure.locate(vehicle.last_latitude, vehicle.last_longitude)
        if offset <= limit:
            vehicle.off_route_since = False
            if open_alert:
                open_alert._close(fix_time)
            return
        if not vehicle.off_route_since:
            vehicle.off_route_since = fix_time
        if open_alert:
            if offset > open_alert.distance_m:
                open_alert.distance_m = offset
        elif fix_time - vehicle.off_route_since >= timedelta(minutes=self._param('off_route_minutes', 3)):
            self._open_alert(vehicle, 'off_route', vehicle.off_route_since, distance_m=offset, threshold=limit)

    @api.model
    def _cron_check(self):
        """Rules that depend on the passage of time rather than on a new position."""
        now = fields.Datetime.now()
        Vehicle = self.env['bus.vehicle']

        offline_minutes = self._param('offline_minutes', 10)
        if offline_minutes > 0:
            silent = Vehicle.search([
                ('last_fix_time', '<', now - timedelta(minutes=offline_minutes)),
                ('last_fix_time', '>', now - RECENTLY_ACTIVE),
            ])
            for bus in silent:
                self._open_alert(bus, 'offline', bus.last_fix_time, threshold=offline_minutes)

        stop_minutes = self._param('long_stop_minutes', 15)
        if stop_minutes > 0:
            parked = Vehicle.search([
                ('last_fix_time', '>=', now - timedelta(minutes=5)),
                ('last_speed', '<=', MOVING_ABOVE_KMH),
                ('current_stop_id', '=', False),
            ])
            for bus in parked:
                last_moving = self.env['bus.position'].search(
                    [('vehicle_id', '=', bus.id), ('speed', '>', MOVING_ABOVE_KMH)],
                    order='fix_time desc', limit=1)
                if last_moving and now - last_moving.fix_time > timedelta(minutes=stop_minutes):
                    self._open_alert(bus, 'long_stop', last_moving.fix_time, threshold=stop_minutes)

    @api.model
    def _cron_push(self):
        """Tell the managers about new alerts. Done here so a slow push service never delays a position."""
        pending = self.search([('notified', '=', False)], limit=50)
        if not pending:
            return
        push = self.env['bus.push.subscription']
        for alert in pending:
            kind = dict(alert._fields['kind']._description_selection(self.env))[alert.kind]
            payload = {
                'title': '%s: %s' % (kind, alert.vehicle_id.name),
                'body': alert.detail or '',
                'url': '/web#id=%d&model=bus.alert&view_type=form' % alert.id,
                'tag': 'bus-alert',
            }
            push._send_to_managers(payload)
            # Marked one by one: whatever happens to the next one, this one is never sent twice.
            alert.notified = True
