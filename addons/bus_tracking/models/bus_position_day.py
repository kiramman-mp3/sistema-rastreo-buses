from datetime import timedelta

from odoo import api, fields, models

from .bus_trip import LOCAL_OFFSET, utc_to_local_date


class BusPositionDay(models.Model):
    """Positions counted per local day, line and kind of bus. Grafana reads these few rows instead of going over
    every position on each refresh, and the counts outlive the positions, which are deleted after a month."""
    _name = 'bus.position.day'
    _description = 'Positions per day'
    _order = 'local_day desc, id desc'

    local_day = fields.Date(required=True, index=True, help="Ecuador date (UTC-5).")
    route_id = fields.Many2one('bus.route', ondelete='set null', index=True)
    simulated = fields.Boolean()
    positions = fields.Integer()
    speed_sum = fields.Float(help="Sum of the speeds (km/h), for the daily average.")

    @api.model
    def _refresh(self, full=False):
        """Count again today and yesterday (a position can arrive late), or every day when the table is empty or
        `full` is set. Earlier days are left as they are: their positions may be gone."""
        self.env.flush_all()
        cr = self.env.cr
        cr.execute("SELECT 1 FROM bus_position_day LIMIT 1")
        if full or not cr.fetchone():
            cr.execute("DELETE FROM bus_position_day")
            since, where = None, ""
        else:
            since = utc_to_local_date(fields.Datetime.now()) - timedelta(days=1)
            cr.execute("DELETE FROM bus_position_day WHERE local_day >= %s", (since,))
            # On the time itself, not on the local date, so the index on fix_time is used.
            where = "WHERE p.fix_time >= %(start)s"
        cr.execute("""
            INSERT INTO bus_position_day (local_day, route_id, simulated, positions, speed_sum,
                                          create_uid, create_date, write_uid, write_date)
            SELECT (p.fix_time - interval '5 hours')::date, v.route_id, COALESCE(v.simulated, false),
                   COUNT(*), SUM(COALESCE(p.speed, 0)),
                   %(uid)s, now() at time zone 'UTC', %(uid)s, now() at time zone 'UTC'
              FROM bus_position p
              JOIN bus_vehicle v ON v.id = p.vehicle_id
            """ + where + """
             GROUP BY 1, 2, 3
        """, {'uid': self.env.uid, 'start': since and fields.Datetime.to_datetime(since) + LOCAL_OFFSET})
        self.invalidate_model()

    @api.model
    def _cron_refresh(self):
        self._refresh()
