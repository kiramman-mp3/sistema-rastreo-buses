from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from .common import BusCase

API = 'odoo.addons.bus_tracking.models.traccar_api.BusTraccarApi'


def stamp(when):
    return when.strftime('%Y-%m-%dT%H:%M:%SZ')


@tagged('post_install', '-at_install')
class TestSyncAudit(BusCase):

    def setUp(self):
        super().setUp()
        self.now = fields.Datetime.now().replace(microsecond=0)
        user = self.env['res.users'].create({'name': 'Chofer', 'login': 'audit-chofer'})
        self.env['bus.shift'].create({
            'user_id': user.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id,
            'start': self.now - timedelta(hours=5)})
        self.times = [self.now - timedelta(minutes=m) for m in (50, 40, 30, 20)]
        for when, lat in zip(self.times[:3], (-33.45, -33.46, -33.47)):
            self.env['bus.position'].create({
                'vehicle_id': self.bus.id, 'fix_time': when, 'latitude': lat, 'longitude': -70.66})

    def traccar(self, extra=()):
        rows = [
            {'fixTime': stamp(self.times[0]), 'latitude': -33.45, 'longitude': -70.66},         # the same
            {'fixTime': stamp(self.times[1]), 'latitude': -33.46, 'longitude': -70.66},         # the same
            {'fixTime': stamp(self.times[2]), 'latitude': -33.50, 'longitude': -70.66},         # another place
            {'fixTime': stamp(self.times[3]), 'latitude': -33.48, 'longitude': -70.66},         # not in Odoo
        ]
        return rows + list(extra)

    def run_audit(self, rows):
        with patch(API + '.is_configured', return_value=True), patch(API + '.get_positions', return_value=rows):
            return self.env['bus.sync.audit']._run(hours=6)

    def test_matching_missing_and_different_positions_are_told_apart(self):
        audit = self.run_audit(self.traccar())
        self.assertEqual((audit.total, audit.matched, audit.missing, audit.mismatched), (4, 2, 1, 1))
        self.assertEqual(audit.accuracy, 50.0)
        self.assertEqual(audit.vehicle_id, self.bus)

    def test_a_position_outside_any_shift_is_not_counted(self):
        """Odoo drops the positions of a bus without a shift on purpose: that is not a synchronisation fault."""
        long_ago = self.now - timedelta(hours=8)
        audit = self.run_audit(self.traccar([{'fixTime': stamp(long_ago), 'latitude': -33.4, 'longitude': -70.6}]))
        self.assertEqual(audit.total, 4)

    def test_all_matching_is_a_perfect_score(self):
        rows = [{'fixTime': stamp(w), 'latitude': lat, 'longitude': -70.66}
                for w, lat in zip(self.times[:3], (-33.45, -33.46, -33.47))]
        audit = self.run_audit(rows)
        self.assertEqual((audit.total, audit.accuracy), (3, 100.0))

    def test_a_bus_with_nothing_to_compare_leaves_no_audit(self):
        self.assertFalse(self.run_audit([]))

    def test_without_traccar_the_audit_says_so(self):
        with patch(API + '.is_configured', return_value=False):
            with self.assertRaises(UserError):
                self.env['bus.sync.audit']._run()
            self.env['bus.sync.audit']._cron_run()                  # the cron stays quiet

    def test_simulated_buses_are_not_audited(self):
        self.bus.simulated = True
        self.assertFalse(self.run_audit(self.traccar()))

    def test_the_audit_asks_traccar_for_the_window_of_the_bus(self):
        with patch(API + '.is_configured', return_value=True), \
                patch(API + '.get_positions', return_value=[]) as asked:
            self.env['bus.sync.audit']._run(hours=2)
        device, since, until = asked.call_args[0]
        self.assertEqual(device, 7)
        self.assertEqual(until - since, timedelta(hours=2))


@tagged('post_install', '-at_install')
class TestTraccarPositionsCall(TransactionCase):

    def test_positions_are_requested_with_the_device_and_the_window(self):
        since = fields.Datetime.now() - timedelta(hours=1)
        until = fields.Datetime.now()
        with patch(API + '._get', return_value=[{'id': 1}]) as get:
            rows = self.env['bus.traccar.api'].get_positions(9, since, until)
        self.assertEqual(rows, [{'id': 1}])
        path, = get.call_args[0]
        params = get.call_args[1]['params']
        self.assertEqual(path, '/positions')
        self.assertEqual(params['deviceId'], 9)
        self.assertTrue(params['from'].endswith('Z') and params['to'].endswith('Z'))

    def test_an_empty_answer_is_an_empty_list(self):
        with patch(API + '._get', return_value=None):
            now = fields.Datetime.now()
            self.assertEqual(self.env['bus.traccar.api'].get_positions(9, now, now), [])


@tagged('post_install', '-at_install')
class TestRejects(BusCase):

    def test_a_refused_position_is_remembered_without_its_content(self):
        reject = self.env['bus.position.reject']._log(
            {'position': {'deviceId': 7, 'latitude': 95.0}, 'device': {'id': 7}}, 'Latitude must be between -90 and 90')
        self.assertEqual(reject.vehicle_id, self.bus)
        self.assertEqual(reject.device_id, 7)
        self.assertIn('Latitude', reject.reason)

    def test_garbage_does_not_break_the_log(self):
        for payload in ({}, {'position': 'x'}, {'device': {'id': 'abc'}}, [], None):
            self.assertTrue(self.env['bus.position.reject']._log(payload, 'nonsense'))

    def test_the_reason_is_cut(self):
        self.assertEqual(len(self.env['bus.position.reject']._log({}, 'x' * 500).reason), 200)

    def test_the_cron_sync_counts_what_it_ignores(self):
        bad = {'deviceId': 7, 'fixTime': 'ayer', 'latitude': -33.4, 'longitude': -70.6}
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.accept_without_shift', '1')
        with patch(API + '.get_latest_positions', return_value=[bad]):
            self.bus._sync_from_traccar()
        self.assertEqual(self.env['bus.position.reject'].search_count([('vehicle_id', '=', self.bus.id)]), 1)


@tagged('post_install', '-at_install')
class TestPerformanceSamples(BusCase):

    def test_the_measurement_times_the_main_queries(self):
        samples = self.env['bus.perf.sample']._measure()
        self.assertEqual(sorted(samples.mapped('name')), ['history', 'indicators', 'live', 'trips'])
        self.assertTrue(all(sample.ms >= 0 for sample in samples))

    def test_old_samples_are_forgotten(self):
        old = self.env['bus.perf.sample'].create({
            'name': 'live', 'ms': 1.0, 'created': fields.Datetime.now() - timedelta(days=120)})
        self.env['bus.perf.sample']._measure()
        self.assertFalse(old.exists())

    def test_the_cron_measures(self):
        before = self.env['bus.perf.sample'].search_count([])
        self.env['bus.perf.sample']._cron_measure()
        self.assertEqual(self.env['bus.perf.sample'].search_count([]), before + 4)
