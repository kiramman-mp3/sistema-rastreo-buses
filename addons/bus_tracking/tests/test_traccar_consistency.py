"""Traccar and Odoo agree: what Traccar forwards reaches Odoo, and the synchronisation audit (indicator S2) says so.

The chain is the real one: the webhook of Odoo receives what Traccar forwards, the pull of the cron asks Traccar for the
latest positions, and the audit compares the two sides. Only the answers of the Traccar API are made up.
"""
import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase, tagged

from .common import traccar_position

API = 'odoo.addons.bus_tracking.models.traccar_api.BusTraccarApi'
WEBHOOK = '/bus_tracking/traccar/webhook?secret=s3cret'


def stamp(when):
    return when.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')


@tagged('post_install', '-at_install')
class TestTraccarOdooConsistency(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].set_param('bus_tracking.webhook_secret', 's3cret')
        self.now = fields.Datetime.now().replace(microsecond=0)
        self.route = self.env['bus.route'].create({'name': 'Linea', 'code': 'LX'})
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus 1', 'route_id': self.route.id, 'traccar_device_id': 7})
        driver = self.env['res.users'].create({'name': 'Chofer', 'login': 'consistency-chofer'})
        self.env['bus.shift'].create({'user_id': driver.id, 'vehicle_id': self.bus.id, 'route_id': self.route.id,
                                      'start': self.now - timedelta(hours=5)})
        # what the phone sent, oldest first: five positions, one every ten minutes
        self.sent = [traccar_position(7, stamp(self.now - timedelta(minutes=50 - 10 * i)), -33.45 - 0.001 * i, -70.66)
                     for i in range(5)]

    def forward(self, positions):
        """What Traccar does for every position it receives: POST it to the webhook of Odoo."""
        for position in positions:
            resp = self.url_open(WEBHOOK, data=json.dumps({'position': position, 'device': {'id': 7}}),
                                 headers={'Content-Type': 'application/json'})
            self.assertEqual(resp.status_code, 200)

    def audit(self):
        """What Traccar has stored for the bus, as its API would answer, against what Odoo has."""
        rows = [{'fixTime': p['fixTime'], 'latitude': p['latitude'], 'longitude': p['longitude']} for p in self.sent]
        with patch(API + '.is_configured', return_value=True), patch(API + '.get_positions', return_value=rows):
            return self.env['bus.sync.audit']._run(hours=6)

    def stored(self):
        return self.env['bus.position'].search_count([('vehicle_id', '=', self.bus.id)])

    def test_everything_forwarded_is_in_odoo_and_the_audit_says_so(self):
        self.forward(self.sent)
        self.assertEqual(self.stored(), 5)
        audit = self.audit()
        self.assertEqual((audit.total, audit.matched, audit.missing, audit.mismatched), (5, 5, 0, 0))
        self.assertEqual(audit.accuracy, 100.0)

    def test_a_forward_that_was_lost_shows_up_as_missing(self):
        self.forward(self.sent[:2] + self.sent[3:])                     # the third one never arrived
        audit = self.audit()
        self.assertEqual((audit.total, audit.matched, audit.missing), (5, 4, 1))
        self.assertEqual(audit.accuracy, 80.0)

    def test_the_same_forward_twice_is_not_a_second_position(self):
        self.forward(self.sent + self.sent[:2])                         # Traccar retries what it forwarded
        self.assertEqual(self.stored(), 5)
        self.assertEqual(self.audit().accuracy, 100.0)

    def test_a_forward_with_the_wrong_secret_is_not_stored_and_the_audit_sees_the_gap(self):
        resp = self.url_open('/bus_tracking/traccar/webhook?secret=wrong', data=json.dumps(
            {'position': self.sent[0], 'device': {'id': 7}}), headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 403)
        self.forward(self.sent[1:])
        self.assertEqual(self.audit().missing, 1)

    def test_the_periodic_pull_recovers_the_latest_position_that_the_webhook_lost(self):
        self.forward(self.sent[:-1])                                    # the newest one was lost on the way
        self.assertEqual(self.audit().accuracy, 80.0)
        icp = self.env['ir.config_parameter']
        icp.set_param('bus_tracking.traccar_url', 'http://traccar:8082')
        icp.set_param('bus_tracking.traccar_user', 'admin@example.com')
        icp.set_param('bus_tracking.traccar_password', 'secret')
        with patch(API + '.get_latest_positions', return_value=[self.sent[-1]]):
            self.env['bus.vehicle']._cron_sync_positions()
        self.assertEqual(self.stored(), 5)
        self.assertEqual(self.audit().accuracy, 100.0)

    def test_the_indicator_reads_the_audits_that_were_made(self):
        self.forward(self.sent[:3])
        self.audit()
        metric = {m['code']: m for m in self.env['bus.kpi'].compute()['metrics']}['S2']
        self.assertEqual(metric['value'], 60.0)                          # 3 of the 5 positions Traccar has
        self.assertIn('3 of 5', metric['detail'])
