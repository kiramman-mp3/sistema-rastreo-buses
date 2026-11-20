from datetime import datetime, timedelta
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import BusCase


@tagged('post_install', '-at_install')
class TestFineStates(BusCase):
    """The life of a fine: proposed, reviewed, confirmed or discarded, appealed once by the driver."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = cls.env['res.users'].create({
            'name': 'Chofer Multas', 'login': 'chofer_multas',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id,
                                  cls.env.ref('bus_tracking.group_bus_driver').id])]})
        cls.manager = cls.env['res.users'].create({
            'name': 'Supervisora', 'login': 'supervisora_multas',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id,
                                  cls.env.ref('bus_tracking.group_bus_manager').id])]})
        cls.viewer = cls.env['res.users'].create({
            'name': 'Operador', 'login': 'operador_multas',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id,
                                  cls.env.ref('bus_tracking.group_bus_user').id])]})
        cls.speeding = cls.env.ref('bus_tracking.fine_type_speeding')

    def _fine(self, **vals):
        values = {
            'type_id': self.speeding.id, 'rule': 'speeding', 'severity': 'serious', 'driver_id': self.driver.id,
            'vehicle_id': self.bus.id, 'occurred_at': fields.Datetime.now() - timedelta(hours=1),
            'amount_proposed': 25.0,
        }
        values.update(vals)
        return self.env['bus.fine'].sudo().create(values)

    def test_seeded_types_follow_the_decisions(self):
        self.assertEqual(self.speeding.threshold, 70)
        self.assertEqual(self.speeding.min_seconds, 30)
        self.assertEqual(self.speeding.currency_id.name, 'USD')
        rules = set(self.env['bus.fine.type'].search([]).mapped('rule'))
        self.assertEqual(rules, {'speeding', 'off_route', 'long_stop', 'skipped_stop', 'late_start',
                                 'incomplete_trip'})

    def test_number_from_the_sequence(self):
        self.assertTrue(self._fine().name.startswith('MUL-'))

    def test_review_then_fine_starts_the_appeal_time(self):
        fine = self._fine().with_user(self.manager)
        fine.action_review()
        self.assertEqual(fine.state, 'review')
        fine.action_fine()
        self.assertEqual(fine.state, 'fined')
        self.assertEqual(fine.amount, 25.0)
        self.assertEqual(fine.reviewer_id, self.manager)
        self.assertAlmostEqual((fine.appeal_deadline - fine.decided_at).days, 3)
        self.assertTrue(fine.can_appeal)

    def test_dragging_a_card_uses_the_same_moves(self):
        fine = self._fine().with_user(self.manager)
        fine.write({'state': 'review'})
        self.assertEqual(fine.state, 'review')
        fine.write({'state': 'fined'})
        self.assertEqual(fine.state, 'fined')
        self.assertTrue(fine.appeal_deadline)
        with self.assertRaises(UserError):
            fine.write({'state': 'new'})
        with self.assertRaises(UserError):
            fine.write({'state': 'appealed'})          # only the driver appeals

    def test_discard_needs_a_reason(self):
        fine = self._fine().with_user(self.manager)
        with self.assertRaises(UserError):
            fine.write({'state': 'discarded'})
        fine.write({'state': 'discarded', 'discard_reason': 'gps'})
        self.assertEqual(fine.state, 'discarded')
        self.assertEqual(fine.discard_reason, 'gps')

    def test_discard_wizard(self):
        fine = self._fine()
        wizard = self.env['bus.fine.discard'].with_user(self.manager).with_context(active_ids=fine.ids).create(
            {'reason': 'justified', 'note': 'Desvío por obra municipal'})
        wizard.action_confirm()
        self.assertEqual(fine.state, 'discarded')
        self.assertEqual(fine.discard_note, 'Desvío por obra municipal')

    def test_a_discarded_fine_can_be_reopened(self):
        fine = self._fine(state='discarded', discard_reason='system').with_user(self.manager)
        fine.action_review()
        self.assertEqual(fine.state, 'review')
        self.assertFalse(fine.discard_reason)

    def test_only_managers_decide(self):
        fine = self._fine()
        with self.assertRaises(AccessError):
            fine.with_user(self.viewer).action_fine()
        with self.assertRaises(AccessError):
            fine.with_user(self.viewer).write({'state': 'review'})
        self.assertEqual(fine.with_user(self.viewer).state, 'new')    # but they can read it

    def test_a_fine_without_driver_cannot_be_confirmed(self):
        fine = self._fine(driver_id=False).with_user(self.manager)
        with self.assertRaises(UserError):
            fine.action_fine()

    def test_appeal_once_within_the_time(self):
        fine = self._fine().with_user(self.manager)
        fine.action_fine()
        with self.assertRaises(ValidationError):
            fine.sudo()._appeal('   ')
        fine.sudo()._appeal('Iba al hospital con un pasajero enfermo')
        self.assertEqual(fine.state, 'appealed')
        self.assertFalse(fine.can_appeal)
        fine.action_reject_appeal()
        self.assertEqual(fine.state, 'fined')
        self.assertEqual(fine.appeal_result, 'rejected')
        with self.assertRaises(UserError):
            fine.sudo()._appeal('Otra vez')               # one statement per fine

    def test_appeal_after_the_deadline_is_refused(self):
        fine = self._fine().with_user(self.manager)
        fine.action_fine()
        later = fields.Datetime.now() + timedelta(days=4)
        with patch.object(fields.Datetime, 'now', return_value=later):
            fine.invalidate_recordset(['can_appeal'])
            with self.assertRaises(UserError):
                fine.sudo()._appeal('Tarde')

    def test_accepted_appeal_discards_the_fine(self):
        fine = self._fine().with_user(self.manager)
        fine.action_fine()
        fine.sudo()._appeal('El GPS falló')
        fine.appeal_answer = 'Se comprobó con el taller'
        fine.action_accept_appeal()
        self.assertEqual(fine.state, 'discarded')
        self.assertEqual(fine.discard_reason, 'appeal_accepted')
        self.assertEqual(fine.amount, 0.0)
        with self.assertRaises(UserError):
            fine.action_review()                          # an accepted appeal is final

    def test_monthly_cap(self):
        self.env['ir.config_parameter'].sudo().set_param('bus_tracking.fines_monthly_cap', 40)
        when = datetime(2026, 11, 10, 15, 0)
        first = self._fine(occurred_at=when).with_user(self.manager)
        second = self._fine(occurred_at=when + timedelta(days=1)).with_user(self.manager)
        first.action_fine()
        second.action_fine()
        self.assertEqual(first.amount, 25.0)
        self.assertEqual(second.amount, 15.0)
        self.assertTrue(second.amount_note)
        next_month = self._fine(occurred_at=datetime(2026, 12, 2, 15, 0)).with_user(self.manager)
        next_month.action_fine()
        self.assertEqual(next_month.amount, 25.0)

    def test_type_values_are_checked(self):
        with self.assertRaises(ValidationError):
            self.speeding.recurrence_factor = 0.5
        with self.assertRaises(ValidationError):
            self.speeding.amount = -1

    def test_one_active_type_per_rule(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint(), mute_logger('odoo.sql_db'):
            self.env['bus.fine.type'].create({'name': 'Otra', 'rule': 'speeding', 'amount': 1})
        self.env['bus.fine.type'].create({'name': 'Vieja', 'rule': 'speeding', 'amount': 1, 'active': False})

    def test_kanban_shows_every_column(self):
        groups = self.env['bus.fine'].read_group([], ['state'], ['state'])
        self.assertEqual([g['state'] for g in groups], ['new', 'review', 'fined', 'appealed', 'discarded'])
