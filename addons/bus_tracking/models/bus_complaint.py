from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

MAX_DESCRIPTION = 2000

KINDS = [
    ('delay', "Delay or missed bus"),
    ('behavior', "Driver or staff behavior"),
    ('safety', "Safety or driving"),
    ('cleanliness', "Cleanliness or condition of the bus"),
    ('other', "Other"),
]


class BusComplaint(models.Model):
    _name = 'bus.complaint'
    _description = 'Passenger Complaint'
    _order = 'create_date desc, id desc'

    name = fields.Char(string="Reference", readonly=True, copy=False, index=True, default='/')
    route_id = fields.Many2one('bus.route', ondelete='set null', index=True)
    vehicle_id = fields.Many2one('bus.vehicle', string="Bus", ondelete='set null', index=True)
    kind = fields.Selection(KINDS, required=True, default='other', index=True)
    description = fields.Text(required=True)
    state = fields.Selection(
        [('new', "New"), ('review', "In review"), ('resolved', "Resolved")],
        required=True, default='new', index=True)
    user_id = fields.Many2one('res.users', string="Responsible", index=True)
    resolved_date = fields.Datetime(readonly=True, copy=False)
    internal_note = fields.Text(help="Visible only to the team.")
    lang = fields.Char(string="Passenger language", help="Language the passenger used, for the reply.")
    # Contact data is optional and only managers can read it.
    contact_email = fields.Char(groups='bus_tracking.group_bus_manager')
    contact_phone = fields.Char(groups='bus_tracking.group_bus_manager')
    has_contact = fields.Boolean(compute='_compute_has_contact', string="Left contact data")

    @api.depends('contact_email', 'contact_phone')
    def _compute_has_contact(self):
        for rec in self.sudo():
            rec.has_contact = bool(rec.contact_email or rec.contact_phone)

    @api.constrains('description')
    def _check_description(self):
        for rec in self:
            if len(rec.description or '') > MAX_DESCRIPTION:
                raise ValidationError(_("The description cannot be longer than %s characters.", MAX_DESCRIPTION))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code('bus.complaint') or '/'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    def action_review(self):
        for rec in self:
            rec.write({'state': 'review', 'resolved_date': False,
                       'user_id': rec.user_id.id or self.env.user.id})

    def action_resolve(self):
        self.write({'state': 'resolved', 'resolved_date': fields.Datetime.now()})

    def action_reopen(self):
        self.write({'state': 'review', 'resolved_date': False})

    @api.model
    def _cron_purge_contacts(self):
        """Erase contact data some days after a complaint was resolved."""
        value = self.env['ir.config_parameter'].sudo().get_param('bus_tracking.complaint_retention_days')
        days = int(value) if value not in (False, None, '') else 90
        if days <= 0:
            return
        limit = fields.Datetime.now() - timedelta(days=days)
        old = self.sudo().search([
            ('state', '=', 'resolved'), ('resolved_date', '<', limit),
            '|', ('contact_email', '!=', False), ('contact_phone', '!=', False)])
        old.write({'contact_email': False, 'contact_phone': False})
