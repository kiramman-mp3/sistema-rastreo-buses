from odoo.tests import HttpCase, TransactionCase, tagged

from ..models.privacy_text import privacy_sections


def flat(sections):
    return ' '.join(' '.join(s['paragraphs'] + s['bullets']) for s in sections)


@tagged('post_install', '-at_install')
class TestPrivacyText(TransactionCase):
    """The text is built from what the system does and from the periods in Settings."""

    def test_both_languages_have_the_same_sections_and_no_loose_placeholders(self):
        es = privacy_sections('es', 'UTA', None, 30, 90)
        en = privacy_sections('en', 'UTA', None, 30, 90)
        self.assertEqual(len(es), len(en))
        for text in (flat(es), flat(en)):
            self.assertNotIn('%', text)
            self.assertNotIn('{', text)
            self.assertNotIn('None', text)

    def test_retention_periods_are_the_configured_ones(self):
        text = flat(privacy_sections('es', 'UTA', None, 45, 120))
        self.assertIn('Las posiciones se conservan 45 días', text)
        self.assertIn('se borran 120 días después de resolver', text)
        self.assertIn('Positions are kept for 45 days', flat(privacy_sections('en', 'UTA', None, 45, 120)))

    def test_without_a_limit_it_says_so_instead_of_inventing_one(self):
        text = flat(privacy_sections('es', 'UTA', None, 0, 0))
        self.assertIn('Las posiciones no se borran solas', text)
        self.assertIn('no se borran solos', text)
        self.assertNotRegex(text, r'(?<![0-9])0 días')  # no "0 days" retention made up

    def test_contact_is_only_what_somebody_typed_in_settings(self):
        with_email = flat(privacy_sections('es', 'UTA', {'email': 'transporte@uta.edu.ec', 'phone': ''}, 30, 90))
        self.assertIn('transporte@uta.edu.ec', with_email)
        nobody = flat(privacy_sections('es', 'UTA', {'email': '', 'phone': ''}, 30, 90))
        self.assertIn('oficina de transporte de UTA', nobody)
        self.assertNotIn('@', nobody)

    def test_it_discloses_the_third_parties_and_the_backups(self):
        text = flat(privacy_sections('es', 'UTA', None, 30, 90))
        for must in ('CARTO', 'session_id', 'copias de seguridad', 'solo mientras tu turno está abierto'):
            self.assertIn(must, text)


@tagged('post_install', '-at_install')
class TestPrivacyPage(HttpCase):

    def setUp(self):
        super().setUp()
        self.icp = self.env['ir.config_parameter'].sudo()
        self.icp.set_param('bus_tracking.retention_days', '30')
        self.icp.set_param('bus_tracking.complaint_retention_days', '90')

    def test_the_page_is_public_and_shows_the_real_periods(self):
        resp = self.url_open('/privacidad')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Las posiciones se conservan 30 días', resp.text)
        self.assertIn('se borran 90 días después de resolver', resp.text)

    def test_the_page_follows_the_language_and_kichwa_reads_spanish(self):
        self.assertIn('Positions are kept for 30 days', self.url_open('/privacidad?lang=en').text)
        self.assertIn('Las posiciones se conservan 30 días', self.url_open('/privacidad?lang=qu').text)

    def test_the_page_follows_a_changed_setting(self):
        self.icp.set_param('bus_tracking.retention_days', '7')
        self.assertIn('Las posiciones se conservan 7 días', self.url_open('/privacidad').text)

    def test_every_public_page_links_to_it_from_the_footer(self):
        for path in ('/rutas', '/quejas', '/privacidad'):
            self.assertIn('href="/privacidad"', self.url_open(path).text, path)

    def test_the_complaint_form_points_to_the_page_of_this_site(self):
        html = self.url_open('/quejas').text
        link = r'<a[^>]*href="/privacidad"[^>]*>'
        self.assertRegex(html, link)
        self.assertRegex(html, r'<p class="privacidad">[^<]*<a[^>]*href="/privacidad"')

    def test_an_official_policy_set_in_settings_replaces_the_link(self):
        self.icp.set_param('bus_tracking.privacy_url', 'https://uta.edu.ec/politica')
        for path in ('/quejas', '/rutas'):
            self.assertIn('href="https://uta.edu.ec/politica"', self.url_open(path).text, path)
        # the page of this site stays reachable
        self.assertEqual(self.url_open('/privacidad').status_code, 200)

    def test_an_unsafe_address_is_ignored(self):
        self.icp.set_param('bus_tracking.privacy_url', 'javascript:alert(1)')
        html = self.url_open('/quejas').text
        self.assertNotIn('javascript:alert', html)
        self.assertIn('href="/privacidad"', html)
