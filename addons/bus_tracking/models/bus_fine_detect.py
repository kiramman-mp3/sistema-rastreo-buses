"""The fine detector: from a closed alert to a proposed fine with its evidence and its checks.

Every figure of a fine is measured again here from the stored positions, not copied from the alert: the alert says
"something happened", the fine says how much, for how long and where, so a person can verify it. The evidence is
kept inside the fine (`evidence_json`) because the positions are deleted after the retention period.

The texts are not stored: the facts and the checks are kept as numbers and keys, and the panel and the tablet
write them in the language of whoever reads them (`_summary_text`, `_check_text`).
"""
import json
import logging
from datetime import timedelta

from odoo import _, api, fields, models

from .bus_trip import LOCAL_OFFSET
from .utils import MOVING_ABOVE_KMH, haversine_m, int_param

_logger = logging.getLogger(__name__)

RULE_KINDS = ('speeding', 'off_route', 'long_stop', 'skipped_stop', 'late_start', 'incomplete_trip')
TRIP_RULES = ('skipped_stop', 'late_start', 'incomplete_trip')
INCIDENT_BEFORE = timedelta(minutes=30)     # an incident this long before the event still explains it
# The largest silence between two positions that still lets the system say what the bus did in between.
MAX_GAP_S = {'speeding': 120, 'off_route': 120, 'long_stop': 300, 'skipped_stop': 180}
EVIDENCE_POINTS = 800


def _iso(moment):
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ') if moment else None


def _local_clock(moment):
    return (moment - LOCAL_OFFSET).strftime('%H:%M') if moment else ''


def _gap_s(points):
    """The largest silence, in seconds, between consecutive positions."""
    return max([(b.fix_time - a.fix_time).total_seconds() for a, b in zip(points, points[1:])] or [0])


def _meters(points):
    return sum(haversine_m(a.latitude, a.longitude, b.latitude, b.longitude) for a, b in zip(points, points[1:]))


def _stretches(positions, inside):
    """Runs of consecutive positions for which `inside(position)` holds."""
    runs, current = [], []
    for position in positions:
        if inside(position):
            current.append(position)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def _duration_s(run):
    return (run[-1].fix_time - run[0].fix_time).total_seconds() if run else 0.0


def _track(positions, flagged=()):
    """The positions as [time, lat, lon, km/h, flag], thinned to what a map needs; flagged ones are always kept."""
    flagged = set(flagged)
    rows = [[_iso(p.fix_time), round(p.latitude, 6), round(p.longitude, 6), round(p.speed, 1),
             1 if p.id in flagged else 0] for p in positions]
    if len(rows) <= EVIDENCE_POINTS:
        return rows
    step = len(rows) / float(EVIDENCE_POINTS)
    keep = {int(i * step) for i in range(EVIDENCE_POINTS)} | {len(rows) - 1}
    return [row for i, row in enumerate(rows) if i in keep or row[4]]


class BusFineDetect(models.Model):
    _inherit = 'bus.fine'

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------
    @api.model
    def _cron_detect(self, limit=200):
        """Look at the closed alerts nobody looked at yet. An alert of a scheduled trip waits until the trip is
        closed, so a late start is measured with the real delay and not with the first warning."""
        Alert = self.env['bus.alert'].sudo()
        Alert.search([('fine_checked', '=', False), ('kind', 'not in', RULE_KINDS)]).write({'fine_checked': True})
        alerts = Alert.search([('fine_checked', '=', False), ('state', '=', 'closed')], order='id', limit=limit)
        return self._detect_alerts(alerts)

    @api.model
    def _detect_alerts(self, alerts):
        fines = self.browse()
        for alert in alerts:
            if alert.kind in TRIP_RULES and alert.trip_id.state in ('planned', 'running'):
                continue
            try:
                with self.env.cr.savepoint():
                    fines |= self.sudo()._detect(alert)
            except Exception:  # noqa: BLE001 - one odd alert must not stop the others; it is retried next time
                _logger.exception("The fine detector failed on alert %s", alert.id)
                continue
            alert.fine_checked = True
        return fines

    @api.model
    def _trigger_detection(self):
        cron = self.env.ref('bus_tracking.cron_detect_fines', raise_if_not_found=False)
        if cron:
            cron.sudo()._trigger()

    @api.model
    def _detect(self, alert):
        """The fine an alert deserves, or nothing when the infraction stays under the threshold of its type."""
        fine_type = self.env['bus.fine.type']._for_rule(alert.kind)
        if not fine_type or self.search_count([('alert_id', '=', alert.id)]):
            return self.browse()
        trip = alert.trip_id
        if alert.kind in TRIP_RULES and trip.state == 'cancelled':
            return self.browse()
        found = getattr(self, '_measure_%s' % alert.kind)(alert, fine_type)
        if not found:
            return self.browse()
        start, end = found['start'], found.get('end') or found['start']
        driver, shift, how = self._driver_for(alert, found)
        incidents = self._incidents_for(alert, start, end)
        checks = [
            {'key': 'driver', 'ok': bool(driver),
             'params': {'name': driver.name if driver else '', 'how': how or ''}},
            {'key': 'incident', 'ok': not incidents,
             'params': {'count': len(incidents), 'kinds': sorted(set(incidents.mapped('kind')))}},
        ] + found['checks'] + [
            {'key': 'threshold', 'ok': True, 'params': {}},
        ]
        ok = all(check['ok'] for check in checks)
        amount, recurrent = self._proposed_amount(fine_type, driver, start)
        vehicle = alert.vehicle_id
        values = {
            'type_id': fine_type.id, 'rule': alert.kind, 'severity': fine_type.severity,
            'driver_id': driver.id if driver else False, 'vehicle_id': vehicle.id,
            'route_id': (alert.route_id or trip.route_id or shift.route_id).id or False,
            'trip_id': trip.id or False, 'shift_id': shift.id or False, 'alert_id': alert.id,
            'simulated': bool(vehicle.simulated or trip.simulated),
            'occurred_at': start, 'ended_at': end,
            'latitude': found.get('lat') or alert.latitude, 'longitude': found.get('lon') or alert.longitude,
            'measured_value': found['value'], 'measured_seconds': int(found.get('seconds') or 0),
            'threshold': fine_type.threshold, 'unit': fine_type.unit,
            'evidence_json': json.dumps(dict(found['evidence'], facts=found['facts']), separators=(',', ':')),
            'checks_json': json.dumps(checks, separators=(',', ':')),
            'checks_ok': ok, 'amount_proposed': amount, 'recurrent': recurrent,
        }
        if not ok:
            values.update({'state': 'discarded', 'discard_reason': 'system', 'decided_at': fields.Datetime.now()})
        return self.with_context(bus_fine_move=True, mail_create_nolog=True).create(values)

    # ------------------------------------------------------------------
    # Who, what else happened, how much
    # ------------------------------------------------------------------
    @api.model
    def _driver_for(self, alert, found):
        """The driver of the bus at the time: the one on a shift, else the driver of the scheduled trip. For the
        rules of a trip the driver of the trip comes first: a late start happens before any shift opens."""
        Shift = self.env['bus.shift'].sudo()
        trip = alert.trip_id
        when = found['start']
        shift = Shift.search([('vehicle_id', '=', alert.vehicle_id.id), ('start', '<=', when),
                              '|', ('end', '=', False), ('end', '>=', when)], order='start desc', limit=1)
        if alert.kind in TRIP_RULES and trip.driver_user_id:
            return trip.driver_user_id, shift, 'trip'
        if shift:
            return shift.user_id, shift, 'shift'
        if trip.driver_user_id:
            return trip.driver_user_id, shift, 'trip'
        return self.env['res.users'], shift, None

    @api.model
    def _incidents_for(self, alert, start, end):
        """Incidents reported by the bus that may explain the event: from a while before it until its end, and
        for the rules of a trip, anything reported on that trip."""
        Incident = self.env['bus.incident'].sudo()
        domain = [('vehicle_id', '=', alert.vehicle_id.id), ('reported_at', '>=', start - INCIDENT_BEFORE),
                  ('reported_at', '<=', end)]
        if alert.kind in TRIP_RULES and alert.trip_id:
            domain = ['|', ('trip_id', '=', alert.trip_id.id)] + ['&'] * (len(domain) - 1) + domain
        return Incident.search(domain)

    @api.model
    def _proposed_amount(self, fine_type, driver, when):
        """The amount of the type, times the repeat factor when the driver already had one confirmed lately."""
        if not driver or fine_type.recurrence_days <= 0:
            return fine_type.amount, False
        before = self.search_count([
            ('driver_id', '=', driver.id), ('type_id', '=', fine_type.id), ('state', 'in', ('fined', 'appealed')),
            ('occurred_at', '<', when), ('occurred_at', '>=', when - timedelta(days=fine_type.recurrence_days))])
        if before:
            return round(fine_type.amount * fine_type.recurrence_factor, 2), True
        return fine_type.amount, False

    @api.model
    def _positions(self, vehicle, start, end):
        return self.env['bus.position'].sudo().search([
            ('vehicle_id', '=', vehicle.id), ('fix_time', '>=', start), ('fix_time', '<=', end)], order='fix_time asc')

    @api.model
    def _route_line(self, route):
        lines = route.sudo()._map_lines() if route else []
        return lines[0]['points'] if lines else []

    @api.model
    def _stops(self, route, statuses=None):
        statuses = statuses or {}
        return [{'name': s.name, 'lat': s.latitude, 'lon': s.longitude, 'radius': s.radius,
                 'status': statuses.get(s.id, '')} for s in route.sudo().stop_ids] if route else []

    @api.model
    def _gps_check(self, points, kind, minimum=2):
        gap = _gap_s(points)
        ok = len(points) >= minimum and gap <= MAX_GAP_S.get(kind, 180)
        return {'key': 'gps', 'ok': ok, 'params': {'points': len(points), 'gap': int(gap),
                                                   'max_gap': MAX_GAP_S.get(kind, 180)}}

    # ------------------------------------------------------------------
    # The rules. Each returns None (no infraction) or what it measured.
    # ------------------------------------------------------------------
    @api.model
    def _measure_speeding(self, alert, fine_type):
        margin = timedelta(minutes=2)
        positions = self._positions(alert.vehicle_id, alert.start_time - margin, (alert.end_time or alert.start_time)
                                    + margin)
        over = [run for run in _stretches(positions, lambda p: p.speed > fine_type.threshold)]
        if not over:
            return None
        run = max(over, key=lambda r: (_duration_s(r), max(p.speed for p in r)))
        seconds = _duration_s(run)
        if (fine_type.min_seconds and (len(run) < 2 or seconds < fine_type.min_seconds)):
            return None
        speeds = [p.speed for p in run]
        limit = int_param(self.env, 'bus_tracking.speed_limit', 50)
        facts = {'threshold': round(fine_type.threshold), 'limit': limit, 'seconds': int(seconds),
                 'min_seconds': fine_type.min_seconds, 'max': round(max(speeds)),
                 'avg': round(sum(speeds) / len(speeds)), 'meters': int(round(_meters(run)))}
        return {
            'start': run[0].fix_time, 'end': run[-1].fix_time, 'value': max(speeds), 'seconds': seconds,
            'lat': run[0].latitude, 'lon': run[0].longitude, 'facts': facts,
            'checks': [self._gps_check(run, 'speeding')],
            'evidence': {'track': _track(positions, [p.id for p in run]),
                         'route': self._route_line(alert.route_id),
                         'chart': {'limit': limit, 'threshold': fine_type.threshold}},
        }

    @api.model
    def _measure_off_route(self, alert, fine_type):
        route = alert.route_id or alert.trip_id.route_id
        measure = route.sudo()._path_measure() if route else None
        corridor = int_param(self.env, 'bus_tracking.off_route_meters', 150) or 150
        margin = timedelta(minutes=3)
        positions = self._positions(alert.vehicle_id, alert.start_time - margin,
                                    (alert.end_time or alert.start_time) + margin)
        if not measure:
            return None
        offsets = {p.id: measure.locate(p.latitude, p.longitude)[1] for p in positions}
        outside = _stretches(positions, lambda p: offsets[p.id] > corridor)
        if not outside:
            return None
        run = max(outside, key=lambda r: (max(offsets[p.id] for p in r), _duration_s(r)))
        farthest = max(offsets[p.id] for p in run)
        seconds = _duration_s(run)
        if farthest <= fine_type.threshold or (fine_type.min_seconds and seconds < fine_type.min_seconds):
            return None
        after = [p for p in positions if p.fix_time > run[-1].fix_time]
        back = after[0] if after else None
        facts = {'corridor': corridor, 'threshold': round(fine_type.threshold), 'max_m': int(round(farthest)),
                 'seconds': int(seconds), 'min_seconds': fine_type.min_seconds,
                 'km': round(_meters(run) / 1000.0, 2),
                 'exit': _local_clock(run[0].fix_time), 'back': _local_clock(back.fix_time) if back else ''}
        return {
            'start': run[0].fix_time, 'end': (back or run[-1]).fix_time, 'value': farthest, 'seconds': seconds,
            'lat': run[0].latitude, 'lon': run[0].longitude, 'facts': facts,
            'checks': [self._gps_check(run, 'off_route')],
            'evidence': {'track': _track(positions, [p.id for p in run]), 'route': self._route_line(route),
                         'corridor_m': corridor, 'stops': self._stops(route)},
        }

    @api.model
    def _measure_long_stop(self, alert, fine_type):
        if not alert.end_time:
            return None
        minutes = (alert.end_time - alert.start_time).total_seconds() / 60.0
        if minutes <= fine_type.threshold:
            return None
        margin = timedelta(minutes=3)
        positions = self._positions(alert.vehicle_id, alert.start_time - margin, alert.end_time + margin)
        still = [p for p in positions if alert.start_time <= p.fix_time <= alert.end_time]
        parked = [p for p in still if p.speed <= MOVING_ABOVE_KMH] or still
        lat = sum(p.latitude for p in parked) / len(parked) if parked else alert.latitude
        lon = sum(p.longitude for p in parked) / len(parked) if parked else alert.longitude
        route = alert.route_id or alert.trip_id.route_id
        nearest, nearest_m = None, None
        for stop in route.sudo().stop_ids if route else []:
            distance = haversine_m(lat, lon, stop.latitude, stop.longitude)
            if nearest_m is None or distance < nearest_m:
                nearest, nearest_m = stop, distance
        if nearest and nearest_m <= nearest.radius:
            return None                 # it was at a stop: waiting there is not a long stop
        facts = {'minutes': int(round(minutes)), 'threshold': round(fine_type.threshold),
                 'from': _local_clock(alert.start_time), 'to': _local_clock(alert.end_time),
                 'nearest': nearest.name if nearest else '', 'nearest_m': int(round(nearest_m or 0))}
        return {
            'start': alert.start_time, 'end': alert.end_time, 'value': minutes, 'seconds': minutes * 60,
            'lat': lat, 'lon': lon, 'facts': facts,
            'checks': [self._gps_check(still, 'long_stop')],
            'evidence': {'track': _track(positions, [p.id for p in parked]), 'route': self._route_line(route),
                         'stops': self._stops(route), 'focus': {'lat': lat, 'lon': lon, 'radius': 40}},
        }

    @api.model
    def _measure_skipped_stop(self, alert, fine_type):
        stop, trip = alert.stop_id, alert.trip_id
        if not stop:
            return None
        if trip:
            lines = trip.stop_line_ids.sorted(lambda ln: (ln.sequence, ln.id))
            line = lines.filtered(lambda ln: ln.stop_id == stop)[:1]
            reached = lines.filtered('actual_time')
            # A stop after the last one reached was not driven past: the trip ended before it (incomplete trip).
            if not line or not reached or line.sequence > reached[-1].sequence:
                return None
            before = reached.filtered(lambda ln: ln.sequence < line.sequence)[-1:]
            after = reached.filtered(lambda ln: ln.sequence > line.sequence)[:1]
            start = before.actual_time or line.planned_time - timedelta(minutes=20)
            end = after.actual_time or line.planned_time + timedelta(minutes=20)
        else:
            start, end = alert.start_time - timedelta(hours=1), alert.start_time
        positions = self._positions(alert.vehicle_id, start, end)
        if positions:
            closest = min(positions, key=lambda p: haversine_m(p.latitude, p.longitude, stop.latitude, stop.longitude))
            closest_m = haversine_m(closest.latitude, closest.longitude, stop.latitude, stop.longitude)
        else:
            closest, closest_m = None, None
        if closest is not None and closest_m <= stop.radius + fine_type.threshold:
            return None
        around = [p for p in positions if closest and abs((p.fix_time - closest.fix_time).total_seconds()) <= 600]
        when = closest.fix_time if closest else (line.planned_time if trip else alert.start_time)
        route = stop.route_id
        statuses = {ln.stop_id.id: ln.status for ln in trip.stop_line_ids} if trip else {}
        facts = {'stop': stop.name, 'radius': stop.radius, 'min_m': int(round(closest_m or 0)),
                 'at': _local_clock(when), 'planned': _local_clock(line.planned_time) if trip else ''}
        return {
            'start': when, 'end': when, 'value': closest_m or 0.0, 'seconds': 0,
            'lat': closest.latitude if closest else stop.latitude,
            'lon': closest.longitude if closest else stop.longitude,
            'facts': facts, 'checks': [self._gps_check(around, 'skipped_stop')],
            'evidence': {'track': _track(positions, [closest.id] if closest else []),
                         'route': self._route_line(route), 'stops': self._stops(route, statuses),
                         'focus': {'lat': stop.latitude, 'lon': stop.longitude, 'radius': stop.radius}},
        }

    @api.model
    def _measure_late_start(self, alert, fine_type):
        trip = alert.trip_id
        if not trip:
            return None
        first = trip.stop_line_ids.sorted(lambda ln: (ln.sequence, ln.id))[:1]
        if trip.real_start:
            delay = (trip.real_start - trip.planned_start).total_seconds() / 60.0
        else:
            margin = timedelta(minutes=int_param(self.env, 'bus_tracking.trip_margin_min', 30))
            delay = ((trip.planned_end or trip.planned_start) + margin - trip.planned_start).total_seconds() / 60.0
        if delay <= fine_type.threshold:
            return None
        start = trip.planned_start - timedelta(minutes=5)
        end = (trip.real_start or trip.planned_end or trip.planned_start) + timedelta(minutes=2)
        positions = self._positions(trip.vehicle_id, start, end)
        at_plan = min(positions, key=lambda p: abs((p.fix_time - trip.planned_start).total_seconds()),
                      default=None)
        away_m = (haversine_m(at_plan.latitude, at_plan.longitude, first.stop_id.latitude, first.stop_id.longitude)
                  if at_plan and first else None)
        facts = {'planned': _local_clock(trip.planned_start), 'real': _local_clock(trip.real_start),
                 'delay': int(round(delay)), 'threshold': round(fine_type.threshold),
                 'started': bool(trip.real_start), 'away_m': int(round(away_m)) if away_m is not None else None,
                 'first': first.stop_id.name or ''}
        return {
            'start': trip.planned_start, 'end': trip.real_start or trip.planned_end, 'value': delay,
            'seconds': delay * 60, 'lat': at_plan.latitude if at_plan else first.stop_id.latitude,
            'lon': at_plan.longitude if at_plan else first.stop_id.longitude, 'facts': facts,
            'checks': [{'key': 'gps', 'ok': bool(positions),
                        'params': {'points': len(positions), 'gap': int(_gap_s(positions)), 'max_gap': 0}}],
            'evidence': {'track': _track(positions, [at_plan.id] if at_plan else []),
                         'route': self._route_line(trip.route_id), 'stops': self._stops(trip.route_id),
                         'focus': ({'lat': first.stop_id.latitude, 'lon': first.stop_id.longitude,
                                    'radius': first.stop_id.radius} if first else None)},
        }

    @api.model
    def _measure_incomplete_trip(self, alert, fine_type):
        trip = alert.trip_id
        if not trip:
            return None
        lines = trip.stop_line_ids.sorted(lambda ln: (ln.sequence, ln.id))
        reached = lines.filtered('actual_time')
        if not reached:
            return None                 # it never started: that is the late start
        missing = lines.filtered(lambda ln: ln.sequence > reached[-1].sequence)
        if len(missing) < max(fine_type.threshold, 1):
            return None                 # only stops in the middle were missed: those are skipped stops
        start = trip.real_start or trip.planned_start
        positions = self._positions(trip.vehicle_id, start, (trip.planned_end or start) + timedelta(minutes=int_param(
            self.env, 'bus_tracking.trip_margin_min', 30)))
        last = positions[-1] if positions else None
        # The signal did not cut out while driving: the last position shows the bus standing still.
        stood = bool(last) and last.speed <= MOVING_ABOVE_KMH
        statuses = {ln.stop_id.id: ln.status for ln in lines}
        facts = {'reached': len(reached), 'total': len(lines), 'missing': len(missing),
                 'last_stop': reached[-1].stop_id.name, 'last_at': _local_clock(last.fix_time if last else None),
                 'missing_names': ', '.join(missing.mapped('stop_id.name'))}
        return {
            'start': reached[-1].actual_time, 'end': last.fix_time if last else reached[-1].actual_time,
            'value': len(missing), 'seconds': 0,
            'lat': last.latitude if last else reached[-1].stop_id.latitude,
            'lon': last.longitude if last else reached[-1].stop_id.longitude, 'facts': facts,
            'checks': [{'key': 'stood', 'ok': stood, 'params': {'speed': round(last.speed, 1) if last else None}}],
            'evidence': {'track': _track(positions, [last.id] if last else []),
                         'route': self._route_line(trip.route_id), 'stops': self._stops(trip.route_id, statuses)},
        }

    # ------------------------------------------------------------------
    # Words, in the language of the reader
    # ------------------------------------------------------------------
    def _evidence(self):
        self.ensure_one()
        try:
            evidence = json.loads(self.evidence_json or '{}')
        except ValueError:
            return {}
        return evidence if isinstance(evidence, dict) else {}

    def _summary_text(self):
        self.ensure_one()
        f = self._evidence().get('facts') or {}
        bus = self.vehicle_id.name or ''
        try:
            if self.rule == 'speeding':
                return _("%(bus)s drove above %(threshold)s km/h for %(seconds)s s in a row (the rule asks for "
                         "%(min_seconds)s s): up to %(max)s km/h, %(avg)s km/h on average over %(meters)s m. The limit "
                         "is %(limit)s km/h, tolerated up to %(threshold)s km/h.", bus=bus, **f)
            if self.rule == 'off_route':
                return _("%(bus)s left its route at %(exit)s and went up to %(max_m)s m away from it (the rule asks "
                         "for more than %(threshold)s m); it drove %(km)s km outside the %(corridor)s m corridor for "
                         "%(seconds)s s.", bus=bus, **f)
            if self.rule == 'long_stop':
                near = (_(" The nearest stop, %(nearest)s, was %(nearest_m)s m away.", **f) if f.get('nearest')
                        else '')
                return _("%(bus)s stood still for %(minutes)s min, from %(from)s to %(to)s, away from the stops of "
                         "its route (the rule allows %(threshold)s min).", bus=bus, **f) + near
            if self.rule == 'skipped_stop':
                return _("%(bus)s drove past %(stop)s at %(at)s without stopping: it came no closer than %(min_m)s m, "
                         "and the stop has a radius of %(radius)s m.", bus=bus, **f)
            if self.rule == 'late_start':
                if f.get('started'):
                    return _("The trip was planned at %(planned)s and %(bus)s reached its first stop at %(real)s: "
                             "%(delay)s min late (the rule allows %(threshold)s min).", bus=bus, **f)
                return _("The trip was planned at %(planned)s and %(bus)s never reached its first stop, "
                         "%(first)s.", bus=bus, **f)
            if self.rule == 'incomplete_trip':
                return _("%(bus)s reached %(reached)s of the %(total)s stops of the trip and stopped after "
                         "%(last_stop)s; it never reached %(missing_names)s.", bus=bus, **f)
        except (KeyError, TypeError, ValueError):
            pass
        return ''

    def _headline_text(self):
        """One line for a kanban card: the figure that makes the fine."""
        self.ensure_one()
        f = self._evidence().get('facts') or {}
        try:
            if self.rule == 'speeding':
                return _("%(max)s km/h · %(seconds)s s above %(threshold)s", **f)
            if self.rule == 'off_route':
                return _("%(max_m)s m off the route · %(minutes)s min", max_m=f['max_m'],
                         minutes=round(f['seconds'] / 60.0, 1))
            if self.rule == 'long_stop':
                return _("Stopped %(minutes)s min", **f)
            if self.rule == 'skipped_stop':
                return _("%(stop)s · passed %(min_m)s m away", **f)
            if self.rule == 'late_start':
                return _("%(delay)s min late", **f) if f.get('started') else _("Never started")
            if self.rule == 'incomplete_trip':
                return _("%(reached)s of %(total)s stops", **f)
        except (KeyError, TypeError, ValueError):
            pass
        return ''

    def _check_text(self, check):
        """(label, detail) of one check, in the language of the reader."""
        key, ok, p = check.get('key'), check.get('ok'), check.get('params') or {}
        if key == 'driver':
            if not ok:
                return _("No driver identified"), _("No shift of the bus and no driver on the trip at that time")
            how = _("on shift") if p.get('how') == 'shift' else _("driver of the scheduled trip")
            return _("Driver identified"), '%s (%s)' % (p.get('name', ''), how)
        if key == 'incident':
            if ok:
                return _("No incident reported"), _("Nothing reported by the bus that explains it")
            labels = dict(self.env['bus.incident']._fields['kind']._description_selection(self.env))
            kinds = ', '.join(labels.get(k, k) for k in p.get('kinds') or [])
            return _("Incident reported"), _("%(count)s incident(s): %(kinds)s", count=p.get('count', 0), kinds=kinds)
        if key == 'gps':
            if p.get('max_gap'):
                detail = _("%(points)s positions, largest silence %(gap)s s (at most %(max_gap)s s)", **p)
            else:
                detail = _("%(points)s positions around the planned time", **p)
            return (_("GPS signal enough") if ok else _("Not enough GPS data to prove it")), detail
        if key == 'stood':
            if ok:
                return _("The bus stopped"), _("The last position shows it standing still: the signal did not cut out "
                                               "while driving")
            return _("The signal cut out while driving"), _("The last position was moving: the end of the trip may "
                                                            "be a lost signal")
        if key == 'threshold':
            return _("Beyond the threshold of the rule"), self.type_id.description or ''
        return key or '', ''

    def _checks_rendered(self):
        self.ensure_one()
        return [dict(zip(('label', 'detail'), self._check_text(check)), ok=bool(check.get('ok')), key=check.get('key'))
                for check in self._checks()]
