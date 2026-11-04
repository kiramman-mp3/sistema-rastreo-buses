"""The indicators of the project: eight about the transport service and four about the software.

Each one has its formula, its source, its unit, its result and an interpretation, and every result is computed by a
SQL query on the stored records (shown with the indicator, so anybody can run it and check the number). Nothing here
is static: add a trip, an alert or a position and the figures move.
"""
from datetime import date, datetime, timedelta

from odoo import _, api, fields, models

from .bus_trip import utc_to_local_date

PERIOD_DAYS = 30

# (good from, acceptable from, higher is better). Between "good" and "acceptable" it is a warning; beyond, bad.
THRESHOLDS = {
    'T1': (90.0, 75.0, True),
    'T2': (85.0, 70.0, True),
    'T3': (5.0, 10.0, False),
    'T4': (95.0, 85.0, True),
    'T5': (50.0, 150.0, False),
    'T6': (5.0, 10.0, False),        # judged on the absolute difference
    'T7': (15.0, 30.0, False),       # judged on the absolute difference with the plan, in %
    'S1': (99.0, 95.0, True),
    'S2': (99.0, 95.0, True),
    'S3': (500.0, 2000.0, False),    # p95 in milliseconds: the project goal is under 2 s
    'S4': (90.0, 75.0, True),
}

# The trips of the period that were closed (done or incomplete), filtered by date, routes and real/simulated.
BASE = """
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
"""
SQL = {
    'T1': BASE + "SELECT COUNT(*) FILTER (WHERE state = 'done'), COUNT(*) FROM f",
    'T2': BASE + """SELECT COUNT(*) FILTER (WHERE s.status <> 'late'), COUNT(*)
                      FROM bus_trip_stop s JOIN f ON f.id = s.trip_id WHERE s.actual_time IS NOT NULL""",
    'T3': BASE + """SELECT AVG(s.delay_min), MAX(s.delay_min), COUNT(*)
                      FROM bus_trip_stop s JOIN f ON f.id = s.trip_id WHERE s.status = 'late'""",
    'T4': BASE + """SELECT COUNT(*) FILTER (WHERE s.actual_time IS NOT NULL), COUNT(*)
                      FROM bus_trip_stop s JOIN f ON f.id = s.trip_id""",
    # Odoo leaves a number that was never written as NULL, and a deviation of exactly 0 m is never written: NULL is 0.
    'T5': BASE + """SELECT AVG(COALESCE(deviation_avg_m, 0)), MAX(COALESCE(deviation_max_m, 0)),
                           AVG(COALESCE(corridor_pct, 0)), COUNT(*)
                      FROM f WHERE distance_real_km > 0""",
    'T6': BASE + """SELECT SUM(distance_est_km), SUM(distance_real_km), COUNT(*)
                      FROM f WHERE distance_real_km > 0""",
    'T7': BASE + """SELECT AVG(duration_real_min), AVG(duration_est_min), COUNT(*)
                      FROM f WHERE state = 'done' AND duration_real_min > 0""",
    'T8': BASE + """SELECT 'alert', a.kind, COUNT(*)
                      FROM bus_alert a JOIN bus_vehicle v ON v.id = a.vehicle_id
                     WHERE (a.start_time - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s
                       AND (%(routes)s::int[] IS NULL OR a.route_id = ANY(%(routes)s::int[]))
                       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT v.simulated)
                            OR (%(scope)s = 'simulated' AND v.simulated))
                     GROUP BY a.kind
                    UNION ALL
                    SELECT 'incident', i.kind, COUNT(*)
                      FROM bus_incident i JOIN bus_vehicle v ON v.id = i.vehicle_id
                     WHERE (i.reported_at - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s
                       AND (%(routes)s::int[] IS NULL OR i.route_id = ANY(%(routes)s::int[]))
                       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT v.simulated)
                            OR (%(scope)s = 'simulated' AND v.simulated))
                     GROUP BY i.kind""",
    'T8km': BASE + "SELECT COALESCE(SUM(distance_real_km), 0) FROM f",
    'S1p': """SELECT COUNT(*) FROM bus_position p JOIN bus_vehicle v ON v.id = p.vehicle_id
               WHERE (p.fix_time - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s
                 AND (%(routes)s::int[] IS NULL OR v.route_id = ANY(%(routes)s::int[]))
                 AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT v.simulated)
                      OR (%(scope)s = 'simulated' AND v.simulated))""",
    'S1r': """SELECT COUNT(*) FROM bus_position_reject r
               WHERE (r.create_date - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s""",
    'S2': """SELECT COALESCE(SUM(matched), 0), COALESCE(SUM(total), 0), COUNT(*) FROM bus_sync_audit
              WHERE (run_at - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s""",
    # S4 reads the expected and the detected flags of the simulated trips and compares them (precision and recall).
    'S4': BASE + "SELECT id FROM f WHERE simulated AND expected_flags IS NOT NULL",
    'S3': """SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY ms), percentile_cont(0.95) WITHIN GROUP (ORDER BY ms),
                    COUNT(*) FROM bus_perf_sample
              WHERE (created - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s""",
}


def pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else None


class BusKpi(models.AbstractModel):
    _name = 'bus.kpi'
    _description = 'Indicators'

    # ------------------------------------------------------------------ definitions (translated)
    @api.model
    def _definitions(self):
        """code: (group, name, unit, formula, source, interpretation). Built on each call so the texts follow
        the language."""
        return {
            'T1': ('transport', _("Route compliance"), '%',
                   _("closed trips that reached every stop ÷ closed trips × 100"),
                   _("bus.trip (state done or incomplete)"),
                   _("Share of the trips that did the whole route. Below 75 % the service is failing its passengers.")),
            'T2': ('transport', _("Punctuality"), '%',
                   _("arrivals not later than the tolerance ÷ arrivals registered × 100"),
                   _("bus.trip.stop (status, with the tolerance of Settings)"),
                   _("Share of the arrivals that were on time or early. An early arrival is not a delay.")),
            'T3': ('transport', _("Average delay"), 'min',
                   _("average of the delay of the late arrivals"),
                   _("bus.trip.stop (status late, delay_min)"),
                   _("How late a late bus is. Up to 5 min is tolerable; beyond 10 min passengers notice it.")),
            'T4': ('transport', _("Stops served"), '%',
                   _("stops with an arrival ÷ stops planned in the closed trips × 100"),
                   _("bus.trip.stop"),
                   _("Share of the planned stops that the buses really reached.")),
            'T5': ('transport', _("Deviation from the route"), 'm',
                   _("average distance of the positions of each trip to the line of the route, averaged over trips"),
                   _("bus.trip (deviation_avg_m, deviation_max_m, corridor_pct)"),
                   _("How far the buses drive from the route. Under 50 m they follow it; over 150 m they leave it.")),
            'T6': ('transport', _("Estimated against driven distance"), '%',
                   _("(km driven − km estimated) ÷ km estimated × 100"),
                   _("bus.trip (distance_est_km, distance_real_km)"),
                   _("Positive: the buses drive more than the route (detours). Within 5 % the estimate is reliable.")),
            'T7': ('transport', _("Average trip time"), 'min',
                   _("average real duration of the trips that reached the last stop; judged against the planned one"),
                   _("bus.trip (duration_real_min, duration_est_min)"),
                   _("Compare with the planned time: within 15 % of the plan the schedule is realistic.")),
            'T8': ('transport', _("Incidents"), 'n',
                   _("number of alerts and driver incidents, and per 100 km driven"),
                   _("bus.alert, bus.incident, bus.trip (distance_real_km)"),
                   _("How often something goes wrong, by kind. Compare the rate per 100 km between routes.")),
            'S1': ('software', _("GPS record integrity"), '%',
                   _("positions stored ÷ (positions stored + positions rejected) × 100"),
                   _("bus.position, bus.position.reject"),
                   _("Share of the received positions that were valid. Rejected ones had impossible data.")),
            'S2': ('software', _("Traccar to Odoo synchronisation accuracy"), '%',
                   _("positions equal in Traccar and Odoo ÷ positions Traccar holds for buses on a shift × 100"),
                   _("bus.sync.audit (compares /api/positions of Traccar with bus.position)"),
                   _("Whether Odoo keeps what Traccar received. Below 95 % positions are being lost.")),
            'S3': ('software', _("Response time"), 'ms',
                   _("95th percentile of the time of the queries behind the map, history, trips and indicators"),
                   _("bus.perf.sample"),
                   _("The project goal is a p95 under 2 000 ms; the median should stay far below it.")),
            'S4': ('software', _("Correct detection of incidents"), '%',
                   _("simulated trips whose detected incidents equal the expected ones ÷ simulated trips × 100"),
                   _("bus.trip (expected_flags, detected_flags of the simulated trips)"),
                   _("How well the rules find what was planted. Precision and recall are in the detail.")),
        }

    @api.model
    def _status(self, code, value):
        """'good', 'warn', 'bad' or 'na' for a value, from the thresholds of the indicator."""
        if value is None or code not in THRESHOLDS:
            return 'na'
        good, ok, higher = THRESHOLDS[code]
        if higher:
            return 'good' if value >= good else 'warn' if value >= ok else 'bad'
        return 'good' if value <= good else 'warn' if value <= ok else 'bad'

    # ------------------------------------------------------------------ period and parameters
    @api.model
    def _period(self, date_from=None, date_to=None):
        def as_date(value, default):
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            return fields.Date.to_date(value) if value else default
        today = utc_to_local_date(fields.Datetime.now())
        d2 = as_date(date_to, today)
        d1 = as_date(date_from, d2 - timedelta(days=PERIOD_DAYS - 1))
        return (d1, d2) if d1 <= d2 else (d2, d1)

    @api.model
    def _params(self, date_from=None, date_to=None, route_ids=None, scope='all'):
        d1, d2 = self._period(date_from, date_to)
        routes = [int(r) for r in route_ids] if route_ids else None
        return {'d1': d1, 'd2': d2, 'routes': routes or None,
                'scope': scope if scope in ('real', 'simulated') else 'all'}

    def _row(self, code, params):
        self.env.cr.execute(SQL[code], params)
        return self.env.cr.fetchone()

    def _rows(self, code, params):
        self.env.cr.execute(SQL[code], params)
        return self.env.cr.fetchall()

    # ------------------------------------------------------------------ the indicators
    @api.model
    def compute(self, date_from=None, date_to=None, route_ids=None, scope='all'):
        """All the indicators for a period (default: the last 30 days), optionally for some routes and for real or
        simulated data only. Returns {'period': ..., 'metrics': [...]} with one dict per indicator."""
        self.env.flush_all()                     # the queries below read the tables, not the cache
        params = self._params(date_from, date_to, route_ids, scope)
        definitions = self._definitions()
        results = {}
        for code, method in (
                ('T1', self._t1), ('T2', self._t2), ('T3', self._t3), ('T4', self._t4), ('T5', self._t5),
                ('T6', self._t6), ('T7', self._t7), ('T8', self._t8), ('S1', self._s1), ('S2', self._s2),
                ('S3', self._s3), ('S4', self._s4)):
            value, detail, judged = method(params)
            group, name, unit, formula, source, interpretation = definitions[code]
            results[code] = {
                'code': code, 'group': group, 'name': name, 'unit': unit, 'formula': formula, 'source': source,
                'interpretation': interpretation, 'value': value, 'detail': detail,
                'status': self._status(code, judged if judged is not None else value),
                'sql': self._shown_sql(code),
            }
        return {'period': {'from': str(params['d1']), 'to': str(params['d2'])}, 'scope': params['scope'],
                'metrics': [results[code] for code in sorted(results, key=lambda c: (c[0] != 'T', int(c[1:])))]}

    @api.model
    def _shown_sql(self, code):
        """The query (or queries) that reproduce an indicator: T8 and S1 use more than one."""
        keys = [key for key in sorted(SQL) if key == code or (key.startswith(code) and len(key) > len(code))]
        separator = chr(10) * 2
        return separator.join(SQL[key].strip() for key in keys)

    def _t1(self, p):
        done, total = self._row('T1', p)
        return pct(done, total), _("%(done)s of %(total)s closed trips", done=done, total=total), None

    def _t2(self, p):
        punctual, total = self._row('T2', p)
        return pct(punctual, total), _("%(n)s of %(total)s arrivals", n=punctual, total=total), None

    def _t3(self, p):
        average, worst, late = self._row('T3', p)
        value = round(float(average), 1) if average is not None else None
        return value, _("%(n)s late arrivals, the worst of %(worst)s min", n=late, worst=round(worst or 0, 1)), None

    def _t4(self, p):
        served, total = self._row('T4', p)
        return pct(served, total), _("%(n)s of %(total)s planned stops", n=served, total=total), None

    def _t5(self, p):
        average, worst, corridor, trips = self._row('T5', p)
        if not trips:
            return None, _("no trips with positions"), None
        return (round(float(average), 1),
                _("worst position %(worst)s m; %(corridor)s %% of the positions inside the corridor",
                  worst=round(worst, 1), corridor=round(float(corridor), 1)), None)

    def _t6(self, p):
        estimated, driven, trips = self._row('T6', p)
        if not estimated:
            return None, _("no trips with positions"), None
        value = round((driven - estimated) / estimated * 100.0, 1)
        return value, _("%(driven)s km driven against %(est)s km estimated", driven=round(driven, 1),
                        est=round(estimated, 1)), abs(value)

    def _t7(self, p):
        real, planned, trips = self._row('T7', p)
        if not trips:
            return None, _("no completed trips"), None
        diff = (real - planned) / planned * 100.0 if planned else 0.0
        return (round(float(real), 1),
                _("planned %(planned)s min (%(diff)s %% against the plan)", planned=round(float(planned), 1),
                  diff=round(diff, 1)), abs(diff))

    def _t8(self, p):
        rows = self._rows('T8', p)
        alerts = sum(n for origin, _kind, n in rows if origin == 'alert')
        incidents = sum(n for origin, _kind, n in rows if origin == 'incident')
        total = alerts + incidents
        km = float(self._row('T8km', p)[0])
        rate = round(total / km * 100.0, 1) if km else None
        by_kind = ', '.join('%s %s' % (kind, n) for _origin, kind, n in sorted(rows, key=lambda r: -r[2])[:4])
        return total, _("%(alerts)s alerts and %(incidents)s incidents; %(rate)s per 100 km. %(kinds)s",
                        alerts=alerts, incidents=incidents, rate=rate if rate is not None else '—', kinds=by_kind), None

    def _s1(self, p):
        stored = self._row('S1p', p)[0]
        rejected = self._row('S1r', p)[0] if p['scope'] != 'simulated' else 0
        detail = _("%(stored)s stored, %(rejected)s rejected", stored=stored, rejected=rejected)
        return pct(stored, stored + rejected), detail, None

    def _s2(self, p):
        matched, total, audits = self._row('S2', p)
        return pct(matched, total), _("%(matched)s of %(total)s positions in %(audits)s audits", matched=matched,
                                      total=total, audits=audits), None

    def _s3(self, p):
        median, p95, samples = self._row('S3', p)
        if not samples:
            return None, _("no samples yet: run the measurement"), None
        return round(float(p95), 1), _("median %(median)s ms in %(n)s samples", median=round(float(median), 1),
                                       n=samples), None

    def _s4(self, p):
        self.env.cr.execute(SQL['S4'], p)
        trips = self.env['bus.trip'].browse([r[0] for r in self.env.cr.fetchall()])
        if not trips:
            return None, _("no simulated trips"), None
        true_pos = false_pos = false_neg = 0
        for trip in trips:
            expected = set(f for f in (trip.expected_flags or '').split(',') if f)
            found = set(f for f in (trip.detected_flags or '').split(',') if f)
            true_pos += len(expected & found)
            false_pos += len(found - expected)
            false_neg += len(expected - found)
        precision = pct(true_pos, true_pos + false_pos)
        recall = pct(true_pos, true_pos + false_neg)
        return (pct(len(trips.filtered('detection_ok')), len(trips)),
                _("precision %(precision)s %%, recall %(recall)s %% over %(n)s simulated trips",
                  precision=precision if precision is not None else '—', recall=recall if recall is not None else '—',
                  n=len(trips)), None)
