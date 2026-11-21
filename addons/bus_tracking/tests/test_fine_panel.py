from odoo.tests import tagged

from .test_driver_auth import make_driver
from .test_fine_detect import FineCase, simulate


@tagged('post_install', '-at_install')
class TestFinePanel(FineCase):
    """What the panel shows of a fine: the card, the form, the menus and the settings."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = make_driver(cls.env, login='jefa_panel', groups='bus_tracking.group_bus_manager')

    def test_every_view_of_a_fine_loads(self):
        views = self.env['bus.fine'].with_user(self.manager).get_views(
            [(False, 'kanban'), (False, 'form'), (False, 'tree'), (False, 'search'), (False, 'graph'),
             (False, 'pivot')])
        self.assertEqual(set(views['views']), {'kanban', 'form', 'tree', 'search', 'graph', 'pivot'})
        self.assertIn('bus_fine_evidence', views['views']['form']['arch'])
        self.env['bus.fine.type'].with_user(self.manager).get_views([(False, 'tree'), (False, 'form')])

    def test_the_card_says_the_figure_of_the_fine(self):
        speeding = self.fines_of(simulate(self.env, self.route, 'speeding', self.driver, days_ago=1))
        self.assertIn('82 km/h', speeding.headline)
        deviation = self.fines_of(simulate(self.env, self.route, 'deviation', self.driver, days_ago=2))
        self.assertIn('m off the route', deviation.headline)
        late = self.fines_of(simulate(self.env, self.route, 'not_started', self.driver, days_ago=3))
        self.assertEqual(late.headline, 'Never started')

    def test_the_menu_opens_the_kanban(self):
        menu = self.env.ref('bus_tracking.menu_bus_fine')
        self.assertEqual(menu.action, self.env.ref('bus_tracking.action_bus_fine'))
        self.assertTrue(self.env.ref('bus_tracking.action_bus_fine').view_mode.startswith('kanban'))

    def test_the_type_opens_its_fines(self):
        fine = self.fines_of(simulate(self.env, self.route, 'speeding', self.driver))
        fine_type = fine.type_id
        self.assertEqual(fine_type.fine_count, 1)
        action = fine_type.action_open_fines()
        self.assertEqual(self.env['bus.fine'].search(action['domain']), fine)

    def test_the_fine_form_has_no_demonstration_notice(self):
        fine = self.fines_of(simulate(self.env, self.route, 'speeding', self.driver))
        self.assertNotIn('demo_notice', fine._fields)
        view = self.env['bus.fine'].get_view(self.env.ref('bus_tracking.view_bus_fine_form').id, 'form')
        self.assertNotIn('Demonstration fine', view['arch'])

    def test_the_discard_button_opens_its_wizard(self):
        fine = self.fines_of(simulate(self.env, self.route, 'speeding', self.driver))
        action = fine.with_user(self.manager).action_open_discard()
        self.assertEqual((action['res_model'], action['target']), ('bus.fine.discard', 'new'))
        self.assertEqual(action['context']['active_ids'], fine.ids)

    def test_the_map_uses_the_tiles_of_the_settings(self):
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.tile_url',
                                                         'https://tiles.example.com/{z}/{x}/{y}.png')
        fine = self.fines_of(simulate(self.env, self.route, 'speeding', self.driver))
        self.assertEqual(fine.map_tile_url, 'https://tiles.example.com/{z}/{x}/{y}.png')
