import re
import time
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import misc

from ..controllers import complaints

MIN_FILL = 'odoo.addons.bus_tracking.controllers.complaints.MIN_FILL_SECONDS'
LONG_TEXT = 'The bus did not stop at Plaza even though I was waiting.'


@tagged('post_install', '-at_install')
class TestComplaintModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Complaint = self.env['bus.complaint']

    def make(self, **vals):
        return self.Complaint.create(dict({'description': LONG_TEXT}, **vals))

    def test_references_are_sequential(self):
        first, second = self.make(), self.make()
        self.assertRegex(first.name, r'^Q-\d{5}$')
        self.assertEqual(int(second.name[2:]), int(first.name[2:]) + 1)

    def test_description_has_a_maximum(self):
        with self.assertRaises(ValidationError):
            self.make(description='x' * 2001)
        self.assertTrue(self.make(description='x' * 2000))

    def test_state_flow(self):
        complaint = self.make()
        self.assertEqual(complaint.state, 'new')
        complaint.action_review()
        self.assertEqual((complaint.state, complaint.user_id), ('review', self.env.user))
        complaint.action_resolve()
        self.assertEqual(complaint.state, 'resolved')
        self.assertTrue(complaint.resolved_date)
        complaint.action_reopen()
        self.assertEqual((complaint.state, complaint.resolved_date), ('review', False))

    def test_review_keeps_an_existing_assignee(self):
        other = self.env['res.users'].create({'name': 'Otro', 'login': 'otro'})
        complaint = self.make(user_id=other.id)
        complaint.action_review()
        self.assertEqual(complaint.user_id, other)

    def test_contact_data_is_erased_after_the_retention_period(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.complaint_retention_days', '30')
        now = fields.Datetime.now()
        old = self.make(contact_email='a@example.org', contact_phone='123456', state='resolved',
                        resolved_date=now - timedelta(days=31))
        recent = self.make(contact_email='b@example.org', state='resolved', resolved_date=now - timedelta(days=5))
        open_old = self.make(contact_email='c@example.org')
        self.env.cr.execute("UPDATE bus_complaint SET create_date = %s WHERE id = %s",
                            (now - timedelta(days=200), open_old.id))
        self.Complaint._cron_purge_contacts()
        self.assertFalse(old.contact_email or old.contact_phone)
        self.assertEqual(recent.contact_email, 'b@example.org')
        self.assertEqual(open_old.contact_email, 'c@example.org')    # unresolved complaints keep it
        self.assertEqual(old.description, LONG_TEXT)                 # the complaint itself stays

    def test_zero_retention_keeps_contact_data(self):
        self.env['ir.config_parameter'].set_param('bus_tracking.complaint_retention_days', '0')
        complaint = self.make(contact_email='a@example.org', state='resolved',
                              resolved_date=fields.Datetime.now() - timedelta(days=900))
        self.Complaint._cron_purge_contacts()
        self.assertEqual(complaint.contact_email, 'a@example.org')

    def test_contact_data_is_only_readable_by_managers(self):
        group = lambda xmlid: self.env.ref(xmlid).id
        viewer = self.env['res.users'].create({
            'name': 'Viewer', 'login': 'viewer2',
            'groups_id': [(6, 0, [group('base.group_user'), group('bus_tracking.group_bus_user')])]})
        manager = self.env['res.users'].create({
            'name': 'Manager', 'login': 'manager2',
            'groups_id': [(6, 0, [group('base.group_user'), group('bus_tracking.group_bus_manager')])]})
        complaint = self.make(contact_email='a@example.org')
        self.assertEqual(complaint.with_user(viewer).description, LONG_TEXT)
        with self.assertRaises(AccessError):
            complaint.with_user(viewer).contact_email
        self.assertEqual(complaint.with_user(manager).contact_email, 'a@example.org')
        with self.assertRaises(AccessError):
            complaint.with_user(viewer).write({'state': 'resolved'})


@tagged('post_install', '-at_install')
class TestComplaintForm(HttpCase):

    def setUp(self):
        super().setUp()
        complaints.submit_limiter.reset()
        patcher = patch(MIN_FILL, 0)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.route = self.env['bus.route'].create({'name': 'Linea Centro', 'code': 'L1'})
        self.other = self.env['bus.route'].create({'name': 'Linea Norte', 'code': 'L2'})
        self.private = self.env['bus.route'].create({'name': 'Privada', 'code': 'P9', 'public': False})
        self.bus = self.env['bus.vehicle'].create({'name': 'Bus 12', 'route_id': self.route.id})
        self.other_bus = self.env['bus.vehicle'].create({'name': 'Bus 77', 'route_id': self.other.id})
        self.private_bus = self.env['bus.vehicle'].create({'name': 'Bus 99', 'route_id': self.private.id})

    # -- helpers ---------------------------------------------------------------
    def form_tokens(self, url='/quejas', **kwargs):
        html = self.url_open(url, **kwargs).text
        return (re.search(r'name="csrf_token" value="([^"]+)"', html).group(1),
                re.search(r'name="t" value="([^"]+)"', html).group(1))

    def submit(self, headers=None, allow_redirects=False, **fields_):
        csrf, token = self.form_tokens()
        data = {'csrf_token': csrf, 't': token, 'route': 'L1', 'bus': str(self.bus.id), 'kind': 'delay',
                'description': LONG_TEXT, 'email': '', 'phone': '', 'website': ''}
        data.update(fields_)
        return self.url_open('/quejas', data=data, headers=headers, allow_redirects=allow_redirects)

    def count(self):
        return self.env['bus.complaint'].search_count([])

    # -- the form page -----------------------------------------------------------
    def test_form_lists_only_public_routes_and_their_buses(self):
        html = self.url_open('/quejas').text
        for text in ('Linea Centro', 'Linea Norte', 'Bus 12', 'Bus 77'):
            self.assertIn(text, html)
        for text in ('Privada', 'Bus 99'):
            self.assertNotIn(text, html)

    def test_form_preselects_the_route_from_the_link(self):
        html = self.url_open('/quejas?ruta=L2').text
        self.assertRegex(html, r'value="L2"\s+selected="selected"')

    def test_route_page_links_to_the_form(self):
        self.assertIn('/quejas?ruta=L1', self.url_open('/rutas/L1').text)

    def test_form_has_the_trap_field_and_a_privacy_notice(self):
        html = self.url_open('/quejas').text
        self.assertIn('name="website"', html)
        self.assertIn('90 días después de resolverlo', html)

    # -- a valid report ----------------------------------------------------------------
    def test_valid_report_is_stored_and_the_passenger_gets_a_reference(self):
        resp = self.submit(email='ana@example.org', phone='+593 99 123 4567')
        self.assertEqual(resp.status_code, 303)
        self.assertRegex(resp.headers['Location'], r'/quejas/gracias\?f=Q-\d{5}&c=1')
        complaint = self.env['bus.complaint'].search([])
        self.assertEqual(len(complaint), 1)
        self.assertEqual((complaint.route_id, complaint.vehicle_id, complaint.kind), (self.route, self.bus, 'delay'))
        self.assertEqual(complaint.description, LONG_TEXT)
        self.assertEqual((complaint.contact_email, complaint.contact_phone), ('ana@example.org', '+593 99 123 4567'))
        self.assertEqual(complaint.state, 'new')
        self.assertEqual(complaint.lang, 'es')
        thanks = self.url_open(resp.headers['Location'])
        self.assertIn(complaint.name, thanks.text)

    def test_anonymous_report_is_accepted_and_says_we_cannot_reply(self):
        resp = self.submit()
        self.assertIn('c=0', resp.headers['Location'])
        self.assertFalse(self.env['bus.complaint'].search([]).has_contact)
        self.assertIn('no podremos responderte', self.url_open(resp.headers['Location']).text)

    def test_every_kind_on_the_form_is_stored_as_chosen(self):
        html = self.url_open('/quejas').text
        for kind in ('delay', 'behavior', 'safety', 'cleanliness', 'other'):
            self.assertIn('value="%s"' % kind, html)
        for fake in ('lost_item', 'conduct'):
            self.assertNotIn('value="%s"' % fake, html)

    def test_report_without_route_or_bus_is_fine(self):
        self.submit(route='', bus='')
        complaint = self.env['bus.complaint'].search([])
        self.assertFalse(complaint.route_id or complaint.vehicle_id)

    def test_unknown_or_private_route_and_foreign_bus_are_ignored(self):
        self.submit(route='NOPE', bus=str(self.bus.id))
        self.submit(route='P9', bus=str(self.private_bus.id))
        self.submit(route='L1', bus=str(self.other_bus.id))       # bus from another route
        for complaint in self.env['bus.complaint'].search([]):
            self.assertFalse(complaint.vehicle_id)
        self.assertEqual(self.env['bus.complaint'].search([('route_id', '=', self.private.id)]).ids, [])

    def test_tampered_kind_becomes_other_and_nul_bytes_are_removed(self):
        self.submit(kind='hack', description=LONG_TEXT + '\x00\x00')
        complaint = self.env['bus.complaint'].search([])
        self.assertEqual(complaint.kind, 'other')
        self.assertEqual(complaint.description, LONG_TEXT)

    # -- validation keeps what the person typed --------------------------------------------
    def test_short_description_is_refused_and_the_form_keeps_the_rest(self):
        resp = self.submit(description='corto', email='ana@example.org', allow_redirects=True)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Escribe entre 10 y 2000 caracteres.', resp.text)
        self.assertIn('ana@example.org', resp.text)
        self.assertEqual(self.count(), 0)

    def test_bad_email_and_phone_are_refused(self):
        resp = self.submit(email='no-es-correo', phone='abc', allow_redirects=True)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Ese correo no parece válido.', resp.text)
        self.assertIn('Ese teléfono no parece válido.', resp.text)
        self.assertEqual(self.count(), 0)

    def test_description_longer_than_the_limit_is_refused(self):
        resp = self.submit(description='x' * 2001, allow_redirects=True)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.count(), 0)

    def test_what_the_person_typed_is_escaped_when_shown_again(self):
        resp = self.submit(description='<script>alert(1)</script>', email='no-es-correo', allow_redirects=True)
        self.assertNotIn('<script>alert(1)</script>', resp.text)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', resp.text)

    def test_messages_follow_the_language(self):
        resp = self.submit(description='short', headers={'Accept-Language': 'en'}, allow_redirects=True)
        self.assertIn('Write between 10 and 2000 characters.', resp.text)

    # -- abuse protection ----------------------------------------------------------------------
    def test_filled_trap_field_stores_nothing_but_looks_like_success(self):
        resp = self.submit(website='http://spam.example')
        self.assertEqual(resp.status_code, 303)
        self.assertTrue(resp.headers['Location'].endswith('/quejas/gracias'))
        self.assertEqual(self.count(), 0)

    def test_posting_too_fast_asks_to_send_again_and_keeps_the_text(self):
        with patch(MIN_FILL, 3):
            resp = self.submit()
        # Not a silent "thanks": a person who pasted the text from the home page would lose it.
        self.assertEqual(resp.status_code, 400)
        self.assertIn('pulsa Enviar otra vez', resp.text)
        self.assertIn(LONG_TEXT, resp.text)
        self.assertEqual(self.count(), 0)

    def test_missing_or_forged_token_stores_nothing(self):
        csrf, _ = self.form_tokens()
        base = {'csrf_token': csrf, 'description': LONG_TEXT, 'kind': 'delay'}
        for token in (None, 'garbage', '1.deadbeef', '%d.%s' % (int(time.time()) - 60, 'f' * 64)):
            data = dict(base) if token is None else dict(base, t=token)
            resp = self.url_open('/quejas', data=data, allow_redirects=False)
            self.assertTrue(resp.headers['Location'].endswith('/quejas/gracias'), token)
        self.assertEqual(self.count(), 0)

    def test_an_expired_form_asks_to_send_again_and_keeps_the_text(self):
        stale = int(time.time()) - 2 * 24 * 3600
        signature = misc.hmac(self.env(su=True), complaints.SCOPE, str(stale))
        csrf, _ = self.form_tokens()
        resp = self.url_open('/quejas', data={
            'csrf_token': csrf, 't': '%d.%s' % (stale, signature),
            'description': LONG_TEXT, 'kind': 'delay'}, allow_redirects=True)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('La página estuvo abierta mucho tiempo', resp.text)
        self.assertIn(LONG_TEXT, resp.text)
        self.assertEqual(self.count(), 0)

    def test_requests_without_a_csrf_token_are_refused(self):
        _, token = self.form_tokens()
        resp = self.url_open('/quejas', data={'t': token, 'description': LONG_TEXT, 'kind': 'delay'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.count(), 0)

    def test_an_address_can_only_send_a_few_reports_per_hour(self):
        statuses = [self.submit().status_code for _ in range(complaints.SUBMIT_LIMIT + 1)]
        self.assertEqual(statuses[:complaints.SUBMIT_LIMIT], [303] * complaints.SUBMIT_LIMIT)
        self.assertEqual(statuses[-1], 429)
        self.assertEqual(self.count(), complaints.SUBMIT_LIMIT)

    def test_oversized_bodies_are_refused(self):
        resp = self.submit(description='x' * (complaints.MAX_BODY_BYTES + 100))
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(self.count(), 0)

    def test_thanks_page_ignores_a_made_up_reference(self):
        html = self.url_open('/quejas/gracias?f=%3Cscript%3Ealert(1)%3C/script%3E').text
        self.assertNotIn('<script>alert(1)', html)
        self.assertNotIn('Tu folio es', html)
