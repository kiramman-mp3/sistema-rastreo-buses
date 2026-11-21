"""Fines proposed to the drivers from the alerts of the system.

The system never fines by itself: it proposes a fine (state New) with the evidence it saw and the checks it made,
and a person reviews it. The driver may answer a confirmed fine from the tablet once (state Appealed).
"""
import json
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .bus_trip import LOCAL_OFFSET
from .utils import int_param, tile_url

RULES = [
    ('speeding', "Speeding"),
    ('off_route', "Off route"),
    ('long_stop', "Long stop"),
    ('skipped_stop', "Skipped stop"),
    ('late_start', "Late start"),
    ('incomplete_trip', "Incomplete trip"),
]
# What the threshold and the measured value of each rule are counted in.
RULE_UNITS = {
    'speeding': 'km/h', 'off_route': 'm', 'long_stop': 'min', 'skipped_stop': 'm', 'late_start': 'min',
    'incomplete_trip': 'stops',
}
SEVERITIES = [('minor', "Minor"), ('serious', "Serious"), ('very_serious', "Very serious")]
SEVERITY_COLOR = {'minor': 3, 'serious': 2, 'very_serious': 1}     # kanban colours: yellow, orange, red
STATES = [
    ('new', "New"),
    ('review', "In review"),
    ('fined', "Fined"),
    ('appealed', "Appealed"),
    ('discarded', "Discarded"),
]
DISCARD_REASONS = [
    ('gps', "GPS false positive"),
    ('justified', "Justified by the circumstances"),
    ('config', "Wrong setup of the rule"),
    ('appeal_accepted', "Appeal accepted"),
    ('system', "Discarded by the system"),
    ('other', "Other"),
]
# The moves a person may make from the panel (buttons or dragging a card). Appealing is the driver's, from the
# tablet; resolving an appeal has its own buttons.
MOVES = {
    'new': {'review', 'fined', 'discarded'},
    'review': {'fined', 'discarded'},
    'fined': set(),
    'appealed': set(),
    'discarded': {'review'},
}
APPEAL_MAX = 1000


class BusFineType(models.Model):
    _name = 'bus.fine.type'
    _description = 'Fine type'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    rule = fields.Selection(RULES, required=True, help="The alert of the system this fine is proposed from.")
    severity = fields.Selection(SEVERITIES, required=True, default='minor')
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self._default_currency())
    amount = fields.Monetary(string="Amount", required=True, default=10.0,
                             help="Amount of a first fine of this type. Demonstration amounts.")
    threshold = fields.Float(
        string="Fine above",
        help="The measured value must go beyond this to be fined: km/h for speeding, metres for a deviation or a "
             "skipped stop, minutes for a late start or a long stop, stops for an incomplete trip.")
    min_seconds = fields.Integer(
        string="For at least (seconds)",
        help="How long the infraction must last. 0: any duration. A single position never counts as a duration.")
    unit = fields.Char(compute='_compute_unit')
    recurrence_days = fields.Integer(
        string="Repeat window (days)", default=30,
        help="A driver with a confirmed fine of this type in this many days before is a repeat offender. 0: never.")
    recurrence_factor = fields.Float(string="Repeat factor", default=1.5,
                                     help="The amount of a repeat offence is multiplied by this.")
    appeal_days = fields.Integer(string="Days to appeal", default=3,
                                 help="How long the driver may answer a confirmed fine from the tablet.")
    description = fields.Text(translate=True, help="What the rule means, shown on each fine.")
    fine_count = fields.Integer(compute='_compute_fine_count')

    def init(self):
        # One active type per rule: the detector must know which one applies.
        self.env.cr.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS bus_fine_type_one_active_rule_idx ON bus_fine_type (rule) WHERE active")

    @api.model
    def _default_currency(self):
        return self.env.ref('base.USD', raise_if_not_found=False) or self.env.company.currency_id

    @api.depends('rule')
    def _compute_unit(self):
        for fine_type in self:
            fine_type.unit = RULE_UNITS.get(fine_type.rule, '')

    def _compute_fine_count(self):
        rows = self.env['bus.fine'].read_group([('type_id', 'in', self.ids)], ['type_id'], ['type_id'])
        counts = {row['type_id'][0]: row['type_id_count'] for row in rows}
        for fine_type in self:
            fine_type.fine_count = counts.get(fine_type.id, 0)

    @api.constrains('amount', 'threshold', 'min_seconds', 'recurrence_days', 'recurrence_factor', 'appeal_days')
    def _check_values(self):
        for fine_type in self:
            if fine_type.amount < 0 or fine_type.threshold < 0 or fine_type.min_seconds < 0:
                raise ValidationError(_("The amount, the threshold and the duration cannot be negative."))
            if fine_type.recurrence_days < 0 or fine_type.appeal_days < 0:
                raise ValidationError(_("The days cannot be negative."))
            if fine_type.recurrence_factor < 1:
                raise ValidationError(_("The repeat factor is 1 or more: a repeat offence never costs less."))

    @api.model
    def _for_rule(self, rule):
        return self.search([('rule', '=', rule)], limit=1)

    def action_open_fines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': self.name, 'res_model': 'bus.fine',
            'view_mode': 'kanban,tree,form', 'domain': [('type_id', '=', self.id)],
        }


class BusFine(models.Model):
    _name = 'bus.fine'
    _description = 'Driver fine'
    _inherit = ['mail.thread']
    _order = 'occurred_at desc, id desc'

    name = fields.Char(string="Number", readonly=True, copy=False, default='/')
    type_id = fields.Many2one('bus.fine.type', string="Type", required=True, ondelete='restrict', index=True)
    rule = fields.Selection(RULES, required=True, index=True)
    severity = fields.Selection(SEVERITIES, required=True)
    state = fields.Selection(STATES, required=True, default='new', index=True, tracking=True,
                             group_expand='_expand_states')
    driver_id = fields.Many2one('res.users', string="Driver", index=True, tracking=True, ondelete='set null')
    vehicle_id = fields.Many2one('bus.vehicle', string="Bus", required=True, index=True, ondelete='cascade')
    route_id = fields.Many2one('bus.route', string="Route", index=True, ondelete='set null')
    trip_id = fields.Many2one('bus.trip', string="Trip", ondelete='set null')
    shift_id = fields.Many2one('bus.shift', string="Shift", ondelete='set null')
    alert_id = fields.Many2one('bus.alert', string="Alert", ondelete='set null', index=True)
    simulated = fields.Boolean(index=True, help="Comes from a trip of the simulator, not from a real bus.")

    occurred_at = fields.Datetime(string="Started at", required=True, index=True)
    ended_at = fields.Datetime(string="Ended at")
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    measured_value = fields.Float(string="Measured", digits=(10, 1))
    measured_seconds = fields.Integer(string="Duration (s)")
    threshold = fields.Float(string="Fine above", digits=(10, 1))
    unit = fields.Char()
    summary = fields.Text(string="Why", compute='_compute_summary',
                          help="Why the system proposes this fine, in plain words.")
    evidence_json = fields.Text(string="Evidence",
                                help="The positions, the route and the stops seen by the system, kept with the fine "
                                     "because the positions themselves are deleted after a while.")
    checks_json = fields.Text(string="Checks")
    checks_ok = fields.Boolean(string="Every check passed")
    check_lines = fields.Html(compute='_compute_check_lines', sanitize=True)

    currency_id = fields.Many2one('res.currency', related='type_id.currency_id')
    amount_proposed = fields.Monetary(string="Proposed amount", readonly=True)
    amount = fields.Monetary(string="Amount", readonly=True, tracking=True)
    amount_note = fields.Char(readonly=True)
    recurrent = fields.Boolean(string="Repeat offence", readonly=True)

    reviewer_id = fields.Many2one('res.users', string="Reviewer", readonly=True, tracking=True)
    decided_at = fields.Datetime(string="Decided at", readonly=True)
    discard_reason = fields.Selection(DISCARD_REASONS, tracking=True)
    discard_note = fields.Text(string="Discard note")

    appeal_deadline = fields.Datetime(string="Appeal until", readonly=True)
    appeal_text = fields.Text(string="Driver's statement", readonly=True)
    appeal_date = fields.Datetime(string="Appealed at", readonly=True)
    appeal_result = fields.Selection([('accepted', "Accepted"), ('rejected', "Rejected")], readonly=True,
                                     tracking=True)
    appeal_answer = fields.Text(string="Answer to the driver")
    can_appeal = fields.Boolean(compute='_compute_can_appeal')
    color = fields.Integer(compute='_compute_color')
    headline = fields.Char(string="In short", compute='_compute_headline')
    map_tile_url = fields.Char(compute='_compute_map_tile_url')

    _sql_constraints = [
        ('alert_uniq', 'unique(alert_id)', "This alert already has a fine."),
    ]

    # ------------------------------------------------------------------
    @api.model
    def _expand_states(self, states, domain, order):
        return [key for key, _label in STATES]

    @api.depends('severity')
    def _compute_color(self):
        for fine in self:
            fine.color = SEVERITY_COLOR.get(fine.severity, 0)

    @api.depends('evidence_json', 'rule')
    @api.depends_context('lang')
    def _compute_headline(self):
        for fine in self:
            fine.headline = fine._headline_text()

    def _compute_map_tile_url(self):
        url = tile_url(self.env)
        for fine in self:
            fine.map_tile_url = url

    @api.depends('state', 'appeal_deadline', 'appeal_text')
    def _compute_can_appeal(self):
        now = fields.Datetime.now()
        for fine in self:
            fine.can_appeal = bool(fine.state == 'fined' and not fine.appeal_text and not fine.appeal_result
                                   and fine.appeal_deadline and now <= fine.appeal_deadline)

    def _checks(self):
        try:
            checks = json.loads(self.checks_json or '[]')
        except ValueError:
            return []
        return checks if isinstance(checks, list) else []

    @api.depends('checks_json')
    @api.depends_context('lang')
    def _compute_check_lines(self):
        for fine in self:
            rows = []
            for check in fine._checks_rendered():
                rows.append('<li class="%s"><span>%s</span> <b>%s</b>%s</li>' % (
                    'o_bus_fine_ok' if check['ok'] else 'o_bus_fine_ko', '✔' if check['ok'] else '✘',
                    _escape(check['label']), (' · %s' % _escape(check['detail'])) if check['detail'] else ''))
            fine.check_lines = '<ul class="o_bus_fine_checks">%s</ul>' % ''.join(rows) if rows else False

    @api.depends('evidence_json', 'rule', 'vehicle_id.name')
    @api.depends_context('lang')
    def _compute_summary(self):
        for fine in self:
            fine.summary = fine._summary_text()

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence'].sudo()
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = sequence.next_by_code('bus.fine') or '/'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Moves
    # ------------------------------------------------------------------
    def _check_manager(self):
        if not (self.env.su or self.env.user.has_group('bus_tracking.group_bus_manager')):
            raise AccessError(_("Only managers can decide on a fine."))

    def write(self, vals):
        """Dragging a card writes the state: it goes through the same moves as the buttons."""
        if 'state' in vals and not self.env.context.get('bus_fine_move'):
            vals = dict(vals)
            target = vals.pop('state')
            if vals:
                super().write(vals)
            for fine in self:
                if fine.state != target:
                    fine._move_to(target)
            return True
        return super().write(vals)

    def _move_to(self, target):
        self.ensure_one()
        if target not in MOVES.get(self.state, set()):
            labels = dict(self._fields['state']._description_selection(self.env))
            if target == 'appealed':
                raise UserError(_("Only the driver can appeal a fine, from the tablet."))
            raise UserError(_("A fine cannot go from %(from)s to %(to)s.",
                              **{'from': labels.get(self.state), 'to': labels.get(target)}))
        if target == 'review':
            self.action_review()
        elif target == 'fined':
            self.action_fine()
        elif target == 'discarded':
            if not self.discard_reason:
                raise UserError(_("Say why the fine is discarded: open it and press Discard."))
            self._discard(self.discard_reason, self.discard_note)

    def _set(self, vals):
        return self.with_context(bus_fine_move=True).write(vals)

    def action_review(self):
        self._check_manager()
        for fine in self:
            accepted = fine.state == 'discarded' and fine.discard_reason == 'appeal_accepted'
            if fine.state not in ('new', 'discarded') or accepted:
                raise UserError(_("Only a new or discarded fine can be reviewed."))
            fine._set({'state': 'review', 'reviewer_id': self.env.user.id, 'discard_reason': False,
                       'discard_note': False, 'decided_at': False})
        return True

    def action_fine(self):
        """Confirm the fine: the amount is final (within the monthly cap) and the driver's appeal time starts."""
        self._check_manager()
        now = fields.Datetime.now()
        for fine in self:
            if fine.state not in ('new', 'review'):
                raise UserError(_("Only a new fine or one in review can be confirmed."))
            if not fine.driver_id:
                raise UserError(_("This fine has no driver: it cannot be confirmed."))
            amount, note = fine._capped_amount()
            fine._set({
                'state': 'fined', 'reviewer_id': self.env.user.id, 'decided_at': now,
                'amount': amount, 'amount_note': note,
                'appeal_deadline': now + timedelta(days=fine.type_id.appeal_days),
            })
        return True

    def _capped_amount(self):
        """The proposed amount, cut to what is left of the driver's monthly cap (0: no cap)."""
        self.ensure_one()
        cap = int_param(self.env, 'bus_tracking.fines_monthly_cap', 0)
        if cap <= 0:
            return self.amount_proposed, False
        local = self.occurred_at - LOCAL_OFFSET
        start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=32)).replace(day=1)
        others = self.sudo().search([
            ('id', '!=', self.id), ('driver_id', '=', self.driver_id.id), ('state', 'in', ('fined', 'appealed')),
            ('occurred_at', '>=', start + LOCAL_OFFSET), ('occurred_at', '<', end + LOCAL_OFFSET)])
        left = max(cap - sum(others.mapped('amount')), 0.0)
        if self.amount_proposed <= left:
            return self.amount_proposed, False
        return left, _("Cut to the monthly cap of %(cap)s per driver.", cap=cap)

    def action_open_discard(self):
        self._check_manager()
        return {
            'type': 'ir.actions.act_window', 'name': _("Discard fine"), 'res_model': 'bus.fine.discard',
            'view_mode': 'form', 'target': 'new', 'context': {'active_ids': self.ids},
        }

    def _discard(self, reason, note=False):
        self._check_manager()
        for fine in self:
            if fine.state not in ('new', 'review') and not (fine.state == 'appealed' and reason == 'appeal_accepted'):
                raise UserError(_("Only a new fine or one in review can be discarded."))
            fine._set({'state': 'discarded', 'discard_reason': reason, 'discard_note': note or False,
                       'reviewer_id': self.env.user.id, 'decided_at': fields.Datetime.now()})
        return True

    def _appeal(self, text):
        """The driver answers a confirmed fine, once and within the time to appeal."""
        self.ensure_one()
        text = (text or '').strip()
        if not text or len(text) > APPEAL_MAX:
            raise ValidationError(_("Write the statement in up to %s characters.", APPEAL_MAX))
        if not self.can_appeal:
            raise UserError(_("This fine can no longer be appealed."))
        self._set({'state': 'appealed', 'appeal_text': text, 'appeal_date': fields.Datetime.now()})
        self.message_post(body=_("The driver appealed: %s", text), author_id=self.driver_id.partner_id.id)
        return True

    def action_accept_appeal(self):
        self._check_manager()
        for fine in self:
            if fine.state != 'appealed':
                raise UserError(_("Only an appealed fine can be resolved."))
            fine._set({'appeal_result': 'accepted', 'amount': 0.0})
            fine._discard('appeal_accepted', fine.appeal_answer)
        return True

    def action_reject_appeal(self):
        self._check_manager()
        for fine in self:
            if fine.state != 'appealed':
                raise UserError(_("Only an appealed fine can be resolved."))
            fine._set({'state': 'fined', 'appeal_result': 'rejected', 'reviewer_id': self.env.user.id,
                       'decided_at': fields.Datetime.now()})
        return True

    def action_open_alert(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'bus.alert', 'res_id': self.alert_id.id,
                'views': [[False, 'form']]}

    def action_open_trip(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'bus.trip', 'res_id': self.trip_id.id,
                'views': [[False, 'form']]}


class BusFineDiscard(models.TransientModel):
    _name = 'bus.fine.discard'
    _description = 'Discard fine'

    reason = fields.Selection([r for r in DISCARD_REASONS if r[0] not in ('appeal_accepted', 'system')],
                              required=True, default='justified')
    note = fields.Text()

    def action_confirm(self):
        fines = self.env['bus.fine'].browse(self.env.context.get('active_ids') or []).exists()
        fines._discard(self.reason, self.note)
        return {'type': 'ir.actions.act_window_close'}


def _escape(text):
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))
