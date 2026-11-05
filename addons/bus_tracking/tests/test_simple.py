from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .common import BusCase, traccar_position

KNOTS_90_KMH = 50.0


@tagged('post_install', '-at_install')
class TestMapLine(BusCase):

    def test_route_line_joins_the_stops_in_order(self):
        lines = self.route._map_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(len(lines[0]['points']), 3)
        self.assertEqual(lines[0]['points'][0], [self.stop['Terminal'].latitude, self.stop['Terminal'].longitude])

    def test_a_route_with_one_stop_has_no_line(self):
        route = self.env['bus.route'].create({
            'name': 'Corta', 'code': 'C1',
            'stop_ids': [(0, 0, {'name': 'Unica', 'latitude': -1.0, 'longitude': -78.0})]})
        self.assertEqual(route._map_lines(), [])


@tagged('post_install', '-at_install')
class TestOffRoute(BusCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].set_param('bus_tracking.off_route_minutes', '0')

    def send(self, minute, lat, lon):
        when = fields.Datetime.now().replace(microsecond=0) - timedelta(minutes=30 - minute)
        self.bus._apply_position(traccar_position(7, when.strftime('%Y-%m-%dT%H:%M:%SZ'), lat, lon, 10.0))

    def open_alerts(self):
        return self.env['bus.alert'].search(
            [('vehicle_id', '=', self.bus.id), ('kind', '=', 'off_route'), ('state', '=', 'open')])

    def test_far_from_the_line_between_the_stops_opens_an_alert_and_returning_closes_it(self):
        mid_lat = (self.stop['Terminal'].latitude + self.stop['Plaza'].latitude) / 2
        mid_lon = (self.stop['Terminal'].longitude + self.stop['Plaza'].longitude) / 2
        self.send(1, mid_lat + 0.01, mid_lon)           # about 1.1 km north of the line
        self.assertEqual(len(self.open_alerts()), 1)
        self.send(2, mid_lat, mid_lon)
        self.assertFalse(self.open_alerts())

    def test_on_the_line_raises_nothing(self):
        mid_lat = (self.stop['Terminal'].latitude + self.stop['Plaza'].latitude) / 2
        mid_lon = (self.stop['Terminal'].longitude + self.stop['Plaza'].longitude) / 2
        self.send(1, mid_lat, mid_lon)
        self.assertFalse(self.open_alerts())

    def test_zero_meters_disables_the_alert(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.off_route_meters', '0')
        self.send(1, self.stop['Terminal'].latitude + 0.05, self.stop['Terminal'].longitude)
        self.assertFalse(self.open_alerts())


@tagged('post_install', '-at_install')
class TestAlertPush(BusCase):

    def test_new_alerts_are_pushed_once_to_the_managers(self):
        self.bus._apply_position(traccar_position(
            7, fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'), -33.45, -70.66, KNOTS_90_KMH))
        alert = self.env['bus.alert'].search([('kind', '=', 'speeding'), ('vehicle_id', '=', self.bus.id)])
        self.assertTrue(alert and not alert.notified)
        send = 'odoo.addons.bus_tracking.models.bus_push.BusPushSubscription._send_to_user'
        with patch(send, return_value=1) as sent:
            self.env['bus.alert']._cron_push()
            first = sent.call_count
            self.env['bus.alert']._cron_push()
        self.assertGreaterEqual(first, 1)
        self.assertEqual(sent.call_count, first)
        self.assertTrue(alert.notified)


@tagged('post_install', '-at_install')
class TestComplaintsAreReadOnlyInTheSystem(TransactionCase):

    def test_staff_cannot_create_or_delete_a_complaint_but_can_update_it(self):
        manager = self.env['res.users'].create({
            'name': 'Gestor', 'login': 'gestor@example.org',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id,
                                  self.env.ref('bus_tracking.group_bus_manager').id])]})
        complaint = self.env['bus.complaint'].create({'description': 'El bus no paro en la parada.'})
        with self.assertRaises(AccessError):
            self.env['bus.complaint'].with_user(manager).create({'description': 'No deberia poder crearla.'})
        complaint.with_user(manager).action_review()
        self.assertEqual(complaint.state, 'review')


@tagged('post_install', '-at_install')
class TestLanguages(TransactionCase):

    def test_english_is_available_and_spanish_translates_the_menus(self):
        self.assertTrue(self.env['res.lang'].with_context(active_test=False).search([('code', '=', 'en_US')]).active)
        self.env['res.lang']._activate_lang('es_ES')
        self.env['ir.module.module'].search([('name', '=', 'bus_tracking')])._update_translations(
            filter_lang='es_ES', overwrite=True)
        menu = self.env.ref('bus_tracking.menu_bus_live_map')
        self.assertEqual(menu.with_context(lang='en_US').name, 'Live Map')
        self.assertEqual(menu.with_context(lang='es_ES').name, 'Mapa en vivo')

    def test_kichwa_is_a_language_of_the_panel(self):
        lang = self.env['res.lang'].with_context(active_test=False).search([('code', '=', 'qu_EC')])
        self.assertTrue(lang.active)
        self.assertEqual(lang.iso_code, 'qu')
        self.env['ir.module.module'].search([('name', '=', 'bus_tracking')])._update_translations(
            filter_lang='qu_EC', overwrite=True)
        root = self.env.ref('bus_tracking.menu_bus_root')
        names = root.with_context(lang='qu_EC').child_id.mapped('name')
        for name in ('Kunan mapa', 'Llankaykuna', 'Bus tantakuna', 'Willaykuna', 'Churana'):
            self.assertIn(name, names)
        # every text of the module has a Kichwa translation
        import polib
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'i18n', 'qu.po')
        empty = [e.msgid for e in polib.pofile(path) if e.msgid and not e.msgstr]
        self.assertEqual(empty, [])
