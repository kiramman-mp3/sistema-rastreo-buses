-- Volume data for qa/rendimiento_volumen.py. Throwaway database only: it EMPTIES the positions, trips, trip stops
-- and alerts and writes them again. Run with:  psql -v positions=100000 -v trips=5000 -f qa/rendimiento_volumen.sql
-- The buses and lines are the ones of scripts/dev_seed.py.
\set ON_ERROR_STOP on
BEGIN;

TRUNCATE bus_trip_stop, bus_alert, bus_trip, bus_position RESTART IDENTITY CASCADE;

CREATE TEMP TABLE perf_bus AS
    SELECT id, route_id, row_number() OVER (ORDER BY id) AS rn
      FROM bus_vehicle WHERE NOT COALESCE(simulated, FALSE) AND route_id IS NOT NULL;
SELECT COUNT(*) AS nbuses FROM perf_bus \gset

-- Positions: one every 5 seconds per bus, going back from a minute ago (what Traccar Client sends).
INSERT INTO bus_position (vehicle_id, latitude, longitude, speed, course, altitude, fix_time,
                          create_uid, write_uid, create_date, write_date)
SELECT b.id,
       -1.2417 + 0.03 * sin(g / 200.0 + b.id), -78.6167 + 0.03 * cos(g / 200.0 + b.id),
       10 + (g % 40), g % 360, 2600,
       (now() AT TIME ZONE 'utc') - ((g / :nbuses) * interval '5 seconds') - interval '1 minute',
       1, 1, now() AT TIME ZONE 'utc', now() AT TIME ZONE 'utc'
  FROM generate_series(0, :positions - 1) g
  JOIN perf_bus b ON b.rn = (g % :nbuses) + 1;

-- The buses on the live map: their last position is the newest one.
UPDATE bus_vehicle v SET last_latitude = p.latitude, last_longitude = p.longitude, last_speed = p.speed,
                         last_fix_time = p.fix_time
  FROM (SELECT DISTINCT ON (vehicle_id) vehicle_id, latitude, longitude, speed, fix_time
          FROM bus_position ORDER BY vehicle_id, fix_time DESC) p
 WHERE p.vehicle_id = v.id;

-- Trips: spread over the last 60 days; one in five incomplete, one in twenty simulated.
INSERT INTO bus_trip (name, vehicle_id, route_id, state, simulated, date, planned_start, planned_end, real_start,
                      real_end, distance_est_km, distance_real_km, duration_est_min, duration_real_min,
                      duration_diff_pct, deviation_avg_m, deviation_max_m, corridor_pct, stops_total, stops_visited,
                      stops_late, stops_skipped, delay_avg_min, delay_max_min, delay_end_min, detected_flags,
                      create_uid, write_uid, create_date, write_date)
SELECT 'PERF-' || g, b.id, b.route_id,
       CASE WHEN g % 5 = 0 THEN 'incomplete' ELSE 'done' END, (g % 20 = 0),
       d, ts, ts + interval '30 minutes', ts + interval '1 minute', ts + interval '32 minutes',
       10.0, 10.0 + (g % 7) * 0.1, 30, 31 + (g % 5), 3.0, 20 + (g % 60), 80 + (g % 200), 90 - (g % 15),
       5, 5 - (g % 5) / 4, (g % 3), (g % 5) / 4, (g % 6)::float, (g % 12)::float, (g % 9)::float,
       CASE WHEN g % 5 = 0 THEN 'incomplete,skipped' WHEN g % 3 = 0 THEN 'late' ELSE '' END,
       1, 1, now() AT TIME ZONE 'utc', now() AT TIME ZONE 'utc'
  FROM generate_series(1, :trips) g
  JOIN perf_bus b ON b.rn = (g % :nbuses) + 1
  CROSS JOIN LATERAL (SELECT ((now() AT TIME ZONE 'utc')::date - (g % 60)) AS d) x
  CROSS JOIN LATERAL (SELECT d::timestamp + interval '12 hours' + ((g % 12) * interval '1 hour') AS ts) y;

-- The stops of each trip: 85 % on time, 10 % late, 5 % skipped.
INSERT INTO bus_trip_stop (trip_id, stop_id, sequence, route_id, vehicle_id, date, status, planned_time, actual_time,
                           delay_min, create_uid, write_uid, create_date, write_date)
SELECT t.id, s.id, s.sequence, t.route_id, t.vehicle_id, t.date, st.status,
       t.planned_start + (COALESCE(s.planned_offset_min, s.sequence / 10 * 4) * interval '1 minute'),
       CASE WHEN st.status = 'skipped' THEN NULL
            ELSE t.planned_start + ((COALESCE(s.planned_offset_min, s.sequence / 10 * 4) + st.delay) * interval '1 minute') END,
       CASE WHEN st.status = 'skipped' THEN NULL ELSE st.delay END, 1, 1,
       now() AT TIME ZONE 'utc', now() AT TIME ZONE 'utc'
  FROM bus_trip t
  JOIN bus_route_stop s ON s.route_id = t.route_id
  CROSS JOIN LATERAL (SELECT (t.id * 7 + s.id) % 20 AS r) x
  CROSS JOIN LATERAL (SELECT CASE WHEN x.r < 17 THEN 'on_time' WHEN x.r < 19 THEN 'late' ELSE 'skipped' END AS status,
                             CASE WHEN x.r < 17 THEN (x.r % 5) - 2 ELSE 6 + (x.r % 4) END AS delay) st;

-- Alerts: one trip in three has one, of the five kinds the rules write.
INSERT INTO bus_alert (vehicle_id, route_id, trip_id, kind, state, start_time, end_time, delay_min,
                       create_uid, write_uid, create_date, write_date)
SELECT t.vehicle_id, t.route_id, t.id,
       (ARRAY['late_arrival', 'skipped_stop', 'off_route', 'speeding', 'offline'])[1 + (t.id % 5)::int],
       'closed', t.planned_start, t.planned_start + interval '5 minutes', (t.id % 14)::float,
       1, 1, now() AT TIME ZONE 'utc', now() AT TIME ZONE 'utc'
  FROM bus_trip t WHERE t.id % 3 = 0;

COMMIT;
ANALYZE bus_position;
ANALYZE bus_trip;
ANALYZE bus_trip_stop;
ANALYZE bus_alert;
SELECT (SELECT COUNT(*) FROM bus_position) AS positions, (SELECT COUNT(*) FROM bus_trip) AS trips,
       (SELECT COUNT(*) FROM bus_trip_stop) AS trip_stops, (SELECT COUNT(*) FROM bus_alert) AS alerts;
