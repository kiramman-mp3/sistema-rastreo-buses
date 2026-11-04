import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    traccar_url = fields.Char(string="Traccar URL", config_parameter='bus_tracking.traccar_url',
                              default='http://traccar:8082')
    traccar_user = fields.Char(string="Traccar user", config_parameter='bus_tracking.traccar_user')
    traccar_password = fields.Char(string="Traccar password", config_parameter='bus_tracking.traccar_password')
    traccar_token = fields.Char(string="Traccar API token", config_parameter='bus_tracking.traccar_token',
                                help="If set, used instead of user/password.")
    bus_gps_url = fields.Char(
        string="GPS address for the phones", config_parameter='bus_tracking.gps_url',
        help="Public HTTPS address the drivers' phones send their position to, e.g. https://gps.example.com.")
    bus_tile_url = fields.Char(
        string="Map tiles", config_parameter='bus_tracking.tile_url',
        help="HTTPS address of the map tiles, with {z}/{x}/{y}. Empty uses CARTO Voyager.")
    bus_accept_without_shift = fields.Boolean(
        string="Accept positions without a shift", config_parameter='bus_tracking.accept_without_shift',
        help="Only for tests with curl or a GPS without the app. Normally a bus only reports while a "
             "driver has it on an open shift.")
    traccar_webhook_secret = fields.Char(string="Webhook secret", config_parameter='bus_tracking.webhook_secret')
    bus_position_retention_days = fields.Integer(
        string="Keep positions (days)", config_parameter='bus_tracking.retention_days', default=30,
        help="Older positions are deleted daily. 0 keeps everything.")
    bus_stale_minutes = fields.Integer(
        string="Report as down after (minutes)", config_parameter='bus_tracking.stale_minutes', default=10,
        help="The health check at /bus_tracking/health fails when no bus has reported for this long. "
             "0 disables the check.")

    bus_speed_limit = fields.Integer(
        string="Speed limit (km/h)", config_parameter='bus_tracking.speed_limit', default=50,
        help="A bus above this speed raises a speeding alert. 0 disables the alert.")
    bus_offline_minutes = fields.Integer(
        string="No-signal alert after (minutes)", config_parameter='bus_tracking.offline_minutes', default=10,
        help="Alert when a bus that was reporting goes silent for this long. 0 disables the alert.")
    bus_long_stop_minutes = fields.Integer(
        string="Long-stop alert after (minutes)", config_parameter='bus_tracking.long_stop_minutes', default=15,
        help="Alert when a bus stays stopped this long away from any stop of its route. 0 disables the alert.")

    bus_off_route_meters = fields.Integer(
        string="Off-route alert beyond (meters)", config_parameter='bus_tracking.off_route_meters', default=150,
        help="Alert when a bus stays this far from the road of its trip. 0 disables the alert.")
    bus_off_route_minutes = fields.Integer(
        string="... for at least (minutes)", config_parameter='bus_tracking.off_route_minutes', default=3)
    bus_trip_horizon_days = fields.Integer(
        string="Create scheduled trips for the next (days)", config_parameter='bus_tracking.trip_horizon_days',
        default=2, help="Every hour the schedules with a default bus create their trips for this many days ahead.")
    bus_punctuality_tolerance = fields.Integer(
        string="Punctuality tolerance (minutes)", config_parameter='bus_tracking.punctuality_tolerance_min', default=5,
        help="An arrival later than the planned time plus this is late; "
             "earlier than the planned time minus this is early.")
    bus_trip_margin = fields.Integer(
        string="Trip window margin (minutes)", config_parameter='bus_tracking.trip_margin_min', default=30,
        help="A stop arrival belongs to a trip when it falls between the planned start and end, "
             "widened by this margin.")
    bus_late_start_minutes = fields.Integer(
        string="Late-start alert after (minutes)", config_parameter='bus_tracking.late_start_minutes', default=10,
        help="Alert when a planned trip has not started this long after its planned departure. 0 disables the alert.")
    bus_time_diff_pct = fields.Integer(
        string="Duration difference flagged beyond (%)", config_parameter='bus_tracking.time_diff_pct', default=25,
        help="A finished trip whose real duration differs from the planned one by more than this is flagged.")
    bus_brand_name = fields.Char(
        string="Name shown to passengers", config_parameter='bus_tracking.brand_name', default='Buses UTA',
        help="Appears on the public pages, the sign-in page and the page titles.")
    bus_map_center = fields.Char(
        string="Map center (latitude, longitude)", config_parameter='bus_tracking.map_center',
        default='-1.2417,-78.6167',
        help="Where the maps open when there is nothing else to show, e.g. -1.2417,-78.6167 for Ambato.")
    bus_privacy_url = fields.Char(
        string="Privacy policy link", config_parameter='bus_tracking.privacy_url',
        help="Optional address of your institution's privacy policy, shown on the complaint form.")
    bus_contact_phone = fields.Char(
        string="Contact phone for passengers", config_parameter='bus_tracking.contact_phone',
        help="Official phone of the transport service. Leave it empty to show no phone on the public pages.")
    bus_contact_email = fields.Char(
        string="Contact email for passengers", config_parameter='bus_tracking.contact_email',
        help="Official email of the transport service. Leave it empty to show no email on the public pages.")
    tablet_setup_link = fields.Char(string="Tablet setup link", compute='_compute_tablet_qr')
    tablet_qr = fields.Binary(string="Tablet QR", compute='_compute_tablet_qr')

    @api.constrains('bus_gps_url')
    def _check_gps_url(self):
        for settings in self:
            value = (settings.bus_gps_url or '').strip()
            if value and not re.match(r'^https?://[^\s/]+(:\d+)?(/\S*)?$', value):
                raise ValidationError(_("The GPS address must look like https://gps.example.com."))

    @api.depends()
    def _compute_tablet_qr(self):
        link, qr = self.env['bus.vehicle']._tablet_setup_pair()
        for rec in self:
            rec.tablet_setup_link = link
            rec.tablet_qr = qr

    bus_complaint_retention_days = fields.Integer(
        string="Erase complaint contact data after (days)", config_parameter='bus_tracking.complaint_retention_days',
        default=90,
        help="Email and phone left in a complaint are erased this many days after it is resolved. 0 keeps them.")

    def action_traccar_test_connection(self):
        conf = {
            'url': (self.traccar_url or '').rstrip('/'),
            'user': self.traccar_user or '',
            'password': self.traccar_password or '',
            'token': self.traccar_token or '',
        }
        devices = self.env['bus.traccar.api'].get_devices(conf=conf)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Traccar"),
                'message': _("Connected. %s device(s) found.", len(devices)),
                'type': 'success',
                'sticky': False,
            },
        }
