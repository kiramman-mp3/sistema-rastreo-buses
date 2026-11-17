import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .utils import int_param

_logger = logging.getLogger(__name__)

# Used until someone saves Settings: a new install must not keep positions forever (DEF-053).
DEFAULT_RETENTION_DAYS = 30
# Arrivals, closed alerts and incidents, finished trips and shifts: the history the reports and Grafana read.
DEFAULT_HISTORY_DAYS = 365

# (table, condition, which deadline). Only what is over: an open alert, an incident nobody has seen yet or an
# active shift is never deleted, whatever its age. Child rows go with their parent (ON DELETE CASCADE).
PURGES = [
    ('bus_position_reject', "create_date < %s", 'positions'),
    ('bus_sync_audit', "run_at < %s", 'positions'),
    ('bus_stop_arrival', "arrival_time < %s", 'history'),
    ('bus_alert', "state = 'closed' AND COALESCE(end_time, start_time) < %s", 'history'),
    ('bus_incident', "state = 'seen' AND reported_at < %s", 'history'),
    ('bus_trip', "state IN ('done', 'incomplete', 'cancelled') AND planned_start < %s", 'history'),
    ('bus_run', "state = 'done' AND departure < %s", 'history'),
    ('bus_shift', "state = 'done' AND \"end\" < %s AND NOT EXISTS ("
                  "SELECT 1 FROM bus_incident i WHERE i.shift_id = bus_shift.id)", 'history'),
]


class BusPosition(models.Model):
    _name = 'bus.position'
    _description = 'Bus Position'
    _order = 'fix_time desc, id desc'

    vehicle_id = fields.Many2one('bus.vehicle', required=True, ondelete='cascade', index=True)
    fix_time = fields.Datetime(required=True, index=True)
    latitude = fields.Float(digits=(10, 7), required=True)
    longitude = fields.Float(digits=(10, 7), required=True)
    speed = fields.Float(help="km/h")
    course = fields.Float(help="Heading in degrees.")
    altitude = fields.Float()
    address = fields.Char()

    _sql_constraints = [
        ('vehicle_fix_uniq', 'unique(vehicle_id, fix_time)', "Duplicate position for this bus and time."),
    ]

    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for rec in self:
            if not (-90.0 <= rec.latitude <= 90.0 and -180.0 <= rec.longitude <= 180.0):
                raise ValidationError(_("Latitude must be between -90 and 90, and longitude between -180 and 180."))

    @api.model
    def _cron_cleanup(self, batch_size=5000):
        days = int_param(self.env, 'bus_tracking.retention_days', DEFAULT_RETENTION_DAYS)
        if days <= 0:
            self._cleanup_history(None, batch_size)
            return
        limit = fields.Datetime.now() - timedelta(days=days)
        self.env.flush_all()
        # Delete in small batches to avoid lock contention, statement timeout, and memory exhaustion
        while True:
            self.env.cr.execute("""
                DELETE FROM bus_position
                WHERE id IN (
                    SELECT id FROM bus_position
                    WHERE fix_time < %s
                    LIMIT %s
                )
            """, (limit, batch_size))
            if self.env.cr.rowcount < batch_size:
                break
        self.env['bus.position'].invalidate_model()
        self._cleanup_traccar(limit)
        self._cleanup_history(limit, batch_size)

    @api.model
    def _cleanup_history(self, positions_limit, batch_size=5000):
        """The other tables that grow with every bus and every day. `positions_limit` None keeps the
        diagnostics, as it keeps the positions."""
        history_days = int_param(self.env, 'bus_tracking.history_retention_days', DEFAULT_HISTORY_DAYS)
        deadline = {
            'positions': positions_limit,
            'history': fields.Datetime.now() - timedelta(days=history_days) if history_days > 0 else None,
        }
        # Raw SQL below: pending ORM writes must reach the database first, or they would land after the deletes.
        self.env.flush_all()
        for table, condition, which in PURGES:
            if deadline[which] is None:
                continue
            while True:
                self.env.cr.execute(
                    "DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE %s LIMIT %%s)" % (table, table, condition),
                    (deadline[which], batch_size))
                if self.env.cr.rowcount < batch_size:
                    break
        self.env.invalidate_all()

    @api.model
    def _cleanup_traccar(self, limit):
        """Traccar keeps its own copy of every position and never deletes it: ask it to drop the same span."""
        api_ = self.env['bus.traccar.api']
        if not api_.is_configured():
            return
        buses = self.env['bus.vehicle'].sudo().with_context(active_test=False).search([('traccar_device_id', '!=', 0)])
        for bus in buses:
            try:
                api_.delete_positions(bus.traccar_device_id, limit)
            except UserError as error:
                _logger.warning("Traccar kept the old positions of %s: %s", bus.name, error)
                return
