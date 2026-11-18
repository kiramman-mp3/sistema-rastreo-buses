from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestNoDiscuss(TransactionCase):

    def test_the_discuss_app_is_hidden_from_everyone(self):
        menu = self.env.ref('mail.menu_root_discuss')
        self.assertFalse(menu.active)
        self.assertNotIn(menu.id, self.env['ir.ui.menu'].with_user(self.env.ref('base.user_admin'))._visible_menu_ids())
