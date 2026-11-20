"""What the dashboard and the PDF report show of the fines of a period."""
from datetime import datetime, time, timedelta

from odoo import _, api, models

from .bus_trip import LOCAL_OFFSET

CONFIRMED = ('fined', 'appealed')
TOP_DRIVERS = 10
MAP_POINTS = 500


def _pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else None


class BusFineStats(models.Model):
    _inherit = 'bus.fine'

    @api.model
    def _period_domain(self, d1, d2, routes=None, scope='all'):
        """The fines that happened between two local dates (both included), on some routes, real or simulated."""
        start = datetime.combine(d1, time.min) + LOCAL_OFFSET
        end = datetime.combine(d2 + timedelta(days=1), time.min) + LOCAL_OFFSET
        domain = [('occurred_at', '>=', start), ('occurred_at', '<', end)]
        if routes:
            domain.append(('route_id', 'in', list(routes)))
        if scope in ('real', 'simulated'):
            domain.append(('simulated', '=', scope == 'simulated'))
        return domain

    @api.model
    def _dashboard(self, d1, d2, routes=None, scope='all'):
        fines = self.search(self._period_domain(d1, d2, routes, scope), order='occurred_at')
        states = [key for key, _label in self._fields['state']._description_selection(self.env)]
        state_labels = dict(self._fields['state']._description_selection(self.env))
        empty = dict.fromkeys(states, 0)

        def by_person(fine):
            """Discarded by a person, not filtered out by the checks of the system."""
            return fine.state == 'discarded' and fine.discard_reason != 'system'

        drivers, types, weeks = {}, {}, {}
        for fine in fines:
            name = fine.driver_id.name or _("No driver")
            row = drivers.setdefault(name, dict(empty, driver=name, amount=0.0, total=0))
            row[fine.state] += 1
            row['total'] += 1
            if fine.state in CONFIRMED:
                row['amount'] += fine.amount

            kind = types.setdefault(fine.type_id.id, dict(empty, type=fine.type_id.name, rule=fine.rule,
                                                          total=0, by_person=0, by_system=0))
            kind[fine.state] += 1
            kind['total'] += 1
            kind['by_person'] += by_person(fine)
            kind['by_system'] += fine.discard_reason == 'system'

            local = (fine.occurred_at - LOCAL_OFFSET).date()
            monday = local - timedelta(days=local.weekday())
            weeks.setdefault(monday, dict(empty))[fine.state] += 1

        for kind in types.values():
            # Precision of the detector: of the fines a person decided on, the share that was right to propose.
            confirmed = kind['fined'] + kind['appealed']
            kind['precision'] = _pct(confirmed, confirmed + kind['by_person'])
        confirmed = fines.filtered(lambda f: f.state in CONFIRMED)
        decided_by_person = len(confirmed) + len(fines.filtered(by_person))
        proposed = fines.filtered(lambda f: f.discard_reason != 'system')
        appeals = fines.filtered('appeal_date')
        currency = (fines[:1].currency_id or self.env['bus.fine.type']._default_currency()).symbol or '$'
        return {
            'currency': currency,
            'state_labels': state_labels,
            'states': states,
            'by_state': {state: len(fines.filtered(lambda f, s=state: f.state == s)) for state in states},
            'metrics': [
                {'code': 'F1', 'name': _("Fines proposed"), 'value': len(proposed), 'unit': 'n', 'status': 'info',
                 'detail': _("%(n)s more filtered out by the checks of the system",
                             n=len(fines) - len(proposed))},
                {'code': 'F2', 'name': _("Waiting for a decision"), 'value': len(fines.filtered(
                    lambda f: f.state in ('new', 'review', 'appealed'))), 'unit': 'n', 'status': 'info',
                 'detail': _("New, in review or appealed")},
                {'code': 'F3', 'name': _("Amount fined"), 'value': round(sum(confirmed.mapped('amount')), 2),
                 'unit': currency, 'status': 'info',
                 'detail': _("%(n)s confirmed fines (fictitious amounts while in demonstration)", n=len(confirmed))},
                {'code': 'F4', 'name': _("Detector precision"), 'value': _pct(len(confirmed), decided_by_person),
                 'unit': '%', 'status': 'info',
                 'detail': _("Confirmed fines over the ones a person decided on")},
                {'code': 'F5', 'name': _("Appeals"), 'value': len(appeals), 'unit': 'n', 'status': 'info',
                 'detail': _("%(n)s accepted", n=len(appeals.filtered(lambda f: f.appeal_result == 'accepted')))},
            ],
            'by_driver': sorted(drivers.values(), key=lambda r: (-r['fined'] - r['appealed'], -r['total'],
                                                                 r['driver']))[:TOP_DRIVERS],
            'by_type': sorted(types.values(), key=lambda r: -r['total']),
            'by_week': [dict(values, week=str(monday)) for monday, values in sorted(weeks.items())],
            'points': [{'lat': f.latitude, 'lon': f.longitude, 'state': f.state, 'rule': f.rule,
                        'label': '%s · %s' % (f.name, f.type_id.name)}
                       for f in fines.filtered(lambda f: f.latitude or f.longitude)[-MAP_POINTS:]],
        }
