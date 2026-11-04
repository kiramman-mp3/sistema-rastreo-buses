"""Read-only SQL views for the business-intelligence tool (Grafana).

Grafana connects with a database role that can read these views and nothing else (see bi/grafana/grafana-role.sql).
The views hold no personal data: no driver, no user, no plate, no free text typed by a person. Times are UTC, as
Grafana filters them; `local_day` is the Ecuador date (UTC-5) the rest of the module uses for "a day".
"""
from odoo import models

ROLE = 'grafana_reader'

VIEWS = {
    'kpi_routes': """
        SELECT r.id AS route_id, r.code AS route_code, r.name AS route_name, r.color,
               COALESCE(r.distance_km, 0)::float AS distance_km, r.active
          FROM bus_route r""",

    'kpi_trips': """
        SELECT t.id AS trip_id,
               COALESCE(t.planned_start, t.real_start, t.date::timestamp + interval '5 hours') AS starts_at,
               t.date AS local_day, r.code AS route_code, r.name AS route_name, v.name AS bus,
               t.state, t.simulated, t.scenario,
               t.planned_start, t.planned_end, t.real_start, t.real_end,
               t.stops_total, t.stops_visited, t.stops_late, t.stops_skipped,
               COALESCE(t.distance_est_km, 0)::float AS distance_est_km,
               COALESCE(t.distance_real_km, 0)::float AS distance_real_km,
               COALESCE(t.duration_est_min, 0) AS duration_est_min,
               COALESCE(t.duration_real_min, 0) AS duration_real_min,
               COALESCE(t.deviation_avg_m, 0) AS deviation_avg_m,
               COALESCE(t.deviation_max_m, 0) AS deviation_max_m,
               COALESCE(t.corridor_pct, 0) AS corridor_pct,
               COALESCE(t.delay_avg_min, 0) AS delay_avg_min,
               COALESCE(t.delay_max_min, 0) AS delay_max_min,
               COALESCE(t.delay_end_min, 0) AS delay_end_min,
               t.detected_flags, t.expected_flags, t.detection_ok
          FROM bus_trip t
          JOIN bus_route r ON r.id = t.route_id
          JOIN bus_vehicle v ON v.id = t.vehicle_id""",

    'kpi_trip_stops': """
        SELECT s.id AS line_id, s.trip_id, t.starts_at, t.local_day, t.route_code, t.bus, t.state AS trip_state,
               t.simulated, st.name AS stop_name, s.sequence, s.status, s.planned_time, s.actual_time,
               COALESCE(s.delay_min, 0) AS delay_min,
               EXTRACT(HOUR FROM (s.planned_time - interval '5 hours'))::int AS local_hour
          FROM bus_trip_stop s
          JOIN kpi_trips t ON t.trip_id = s.trip_id
          JOIN bus_route_stop st ON st.id = s.stop_id""",

    # Alerts raised by the rules and incidents reported by the drivers (only the kind: the note is free text).
    'kpi_alerts': """
        SELECT 'alert'::text AS origin, a.id AS event_id, a.start_time AS happened_at,
               (a.start_time - interval '5 hours')::date AS local_day, a.kind, r.code AS route_code, v.name AS bus,
               v.simulated, a.trip_id, COALESCE(a.delay_min, 0) AS delay_min, COALESCE(a.distance_m, 0) AS distance_m,
               COALESCE(a.max_speed, 0) AS max_speed
          FROM bus_alert a
          JOIN bus_vehicle v ON v.id = a.vehicle_id
          LEFT JOIN bus_route r ON r.id = a.route_id
        UNION ALL
        SELECT 'incident'::text, i.id, i.reported_at, (i.reported_at - interval '5 hours')::date, i.kind,
               r.code, v.name, v.simulated, i.trip_id, 0, 0, 0
          FROM bus_incident i
          JOIN bus_vehicle v ON v.id = i.vehicle_id
          LEFT JOIN bus_route r ON r.id = i.route_id""",

    # The positions of each trip: what draws the path of a trip on a map.
    'kpi_positions': """
        SELECT p.id AS position_id, t.trip_id, p.fix_time, t.route_code, t.bus, t.simulated,
               p.latitude::float AS latitude, p.longitude::float AS longitude, COALESCE(p.speed, 0) AS speed
          FROM bus_position p
          JOIN kpi_trips t ON t.real_start IS NOT NULL
           AND p.vehicle_id = (SELECT vehicle_id FROM bus_trip WHERE id = t.trip_id)
           AND p.fix_time BETWEEN t.real_start AND COALESCE(t.real_end, t.real_start + interval '12 hours')""",

    'kpi_positions_daily': """
        SELECT (p.fix_time - interval '5 hours')::date AS local_day, r.code AS route_code, v.simulated,
               COUNT(*) AS positions, AVG(COALESCE(p.speed, 0)) AS avg_speed
          FROM bus_position p
          JOIN bus_vehicle v ON v.id = p.vehicle_id
          LEFT JOIN bus_route r ON r.id = v.route_id
         GROUP BY 1, 2, 3""",

    # The four software indicators (S1 to S4), one row per day with something to say.
    'kpi_software': """
        WITH stored AS (
            SELECT (fix_time - interval '5 hours')::date AS d, COUNT(*) AS n FROM bus_position GROUP BY 1
        ), rejected AS (
            SELECT (create_date - interval '5 hours')::date AS d, COUNT(*) AS n FROM bus_position_reject GROUP BY 1
        ), audits AS (
            SELECT (run_at - interval '5 hours')::date AS d, SUM(matched) AS matched, SUM(total) AS total
              FROM bus_sync_audit GROUP BY 1
        ), perf AS (
            SELECT (created - interval '5 hours')::date AS d,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY ms) AS p50,
                   percentile_cont(0.95) WITHIN GROUP (ORDER BY ms) AS p95, COUNT(*) AS samples
              FROM bus_perf_sample GROUP BY 1
        ), detection AS (
            SELECT date AS d, COUNT(*) AS trips, COUNT(*) FILTER (WHERE detection_ok) AS ok
              FROM bus_trip WHERE simulated AND expected_flags IS NOT NULL AND state IN ('done', 'incomplete')
             GROUP BY 1
        ), days AS (
            SELECT d FROM stored UNION SELECT d FROM rejected UNION SELECT d FROM audits
            UNION SELECT d FROM perf UNION SELECT d FROM detection
        )
        SELECT days.d AS local_day, (days.d::timestamp + interval '5 hours') AS day_start,
               COALESCE(stored.n, 0) AS positions_stored, COALESCE(rejected.n, 0) AS positions_rejected,
               COALESCE(audits.matched, 0) AS audit_matched, COALESCE(audits.total, 0) AS audit_total,
               perf.p50 AS response_p50_ms, perf.p95 AS response_p95_ms, COALESCE(perf.samples, 0) AS response_samples,
               COALESCE(detection.trips, 0) AS simulated_trips, COALESCE(detection.ok, 0) AS detected_ok
          FROM days
          LEFT JOIN stored ON stored.d = days.d LEFT JOIN rejected ON rejected.d = days.d
          LEFT JOIN audits ON audits.d = days.d LEFT JOIN perf ON perf.d = days.d
          LEFT JOIN detection ON detection.d = days.d""",
}

# The creation order matters: a view that reads another one comes after it.
ORDER = ['kpi_routes', 'kpi_trips', 'kpi_trip_stops', 'kpi_alerts', 'kpi_positions', 'kpi_positions_daily',
         'kpi_software']


def grant_views(cr, role=ROLE):
    """Lets the role read every kpi_* view (and only them), when the role exists."""
    cr.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
    if cr.fetchone():
        cr.execute('GRANT SELECT ON %s TO "%s"' % (', '.join(ORDER), role))


class BusKpiViews(models.Model):
    """Holds nothing: it exists to create the views each time the module is installed or updated."""
    _name = 'bus.kpi.views'
    _description = 'SQL views for the business-intelligence tool'
    _auto = False
    _table = 'kpi_routes'          # the first view: the registry wants a table that exists

    def init(self):
        cr = self.env.cr
        for name in reversed(ORDER):
            cr.execute('DROP VIEW IF EXISTS %s CASCADE' % name)
        for name in ORDER:
            cr.execute('CREATE VIEW %s AS %s' % (name, VIEWS[name]))
        grant_views(cr)
