"""The link with Odoo Fleet.

Fleet is where a transport company keeps its vehicles: plate, driver, seats, contracts, services, costs. `bus.vehicle`
stays what it is, the tracking side of a bus (Traccar device, last position, alerts, shifts, trips), and each bus
points to its `fleet.vehicle`. The two share the facts they both have: the plate, the driver, the seats and whether it
is active; change one and the other follows. A bus made by the trip simulator is not a vehicle of the company and
never reaches Fleet.
"""
from odoo import _, api, fields, models

SYNC = 'bus_fleet_sync'            # in the context while one side copies to the other, so it does not bounce back
# bus.vehicle field -> fleet.vehicle field
TO_FLEET = {'plate': 'license_plate', 'driver_id': 'driver_id', 'capacity': 'seats', 'active': 'active'}
TO_BUS = {fleet: bus for bus, fleet in TO_FLEET.items()}


class BusVehicle(models.Model):
    _inherit = 'bus.vehicle'

    fleet_vehicle_id = fields.Many2one(
        'fleet.vehicle', string="Fleet vehicle", copy=False, index=True, ondelete='set null',
        help="The vehicle of the company in Fleet. It is created with the bus; the plate, the driver, the seats "
             "and the active flag are the same in both.")

    _sql_constraints = [
        ('fleet_vehicle_uniq', 'unique(fleet_vehicle_id)', "This Fleet vehicle already belongs to another bus."),
    ]

    def _fleet_values(self):
        self.ensure_one()
        return {'license_plate': self.plate or False, 'driver_id': self.driver_id.id, 'seats': self.capacity,
                'active': self.active}

    def _fleet_model(self):
        return self.env.ref('bus_tracking.fleet_model_bus').sudo()

    def _link_fleet(self):
        """Gives each bus of the company its Fleet vehicle: the one that already has its plate, or a new one.
        Safe to repeat: a bus that is already linked is left alone. Returns the buses that were linked."""
        Fleet = self.env['fleet.vehicle'].sudo().with_context(active_test=False)
        everyone = self.sudo().with_context(active_test=False)
        linked = self.browse()
        for bus in self.filtered(lambda b: not b.simulated and not b.fleet_vehicle_id):
            vehicle = Fleet.browse()
            if bus.plate:
                vehicle = Fleet.search([('license_plate', '=', bus.plate), ('model_id', '!=', False)]).filtered(
                    lambda v: not everyone.search_count([('fleet_vehicle_id', '=', v.id)]))[:1]
            if not vehicle:
                vals = dict(bus._fleet_values(), model_id=bus._fleet_model().id)
                vehicle = Fleet.with_context(**{SYNC: True}).create(vals)
            bus.with_context(**{SYNC: True}).fleet_vehicle_id = vehicle
            linked |= bus
        return linked

    @api.model_create_multi
    def create(self, vals_list):
        buses = super().create(vals_list)
        if not self.env.context.get(SYNC):
            buses._link_fleet()
        return buses

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get(SYNC) and TO_FLEET.keys() & vals.keys():
            for bus in self.filtered('fleet_vehicle_id'):
                shared = bus._fleet_values()
                values = {fleet: shared[fleet] for bus_field, fleet in TO_FLEET.items() if bus_field in vals}
                bus.fleet_vehicle_id.sudo().with_context(**{SYNC: True}).write(values)
        return result

    def _sync_fleet_route(self):
        """Tells each Fleet vehicle whether its bus is driving a shift now, for the En ruta column."""
        Shift = self.env['bus.shift'].sudo()
        for bus in self.sudo().with_context(active_test=False).filtered('fleet_vehicle_id'):
            on_route = bool(Shift.search_count([('vehicle_id', '=', bus.id), ('state', '=', 'active')]))
            if bus.fleet_vehicle_id.bus_on_route != on_route:
                bus.fleet_vehicle_id.with_context(**{SYNC: True}).bus_on_route = on_route

    def action_open_fleet(self):
        self.ensure_one()
        if not self.fleet_vehicle_id:
            self._link_fleet()
        return {
            'type': 'ir.actions.act_window', 'name': _("Fleet vehicle"), 'res_model': 'fleet.vehicle',
            'res_id': self.fleet_vehicle_id.id, 'view_mode': 'form', 'target': 'current',
        }


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    bus_id = fields.Many2one(
        'bus.vehicle', string="Tracked as bus", compute='_compute_bus',
        search='_search_bus_id', compute_sudo=True)
    bus_traccar_device_id = fields.Integer(string="GPS device (Traccar)", related='bus_id.traccar_device_id')
    bus_connection = fields.Selection(related='bus_id.connection', string="GPS connection")
    bus_last_fix_time = fields.Datetime(related='bus_id.last_fix_time', string="Last position")
    bus_route_id = fields.Many2one('bus.route', string="Route", related='bus_id.route_id', readonly=False)
    bus_status = fields.Selection(related='bus_id.status', string="Status")
    bus_current_stop_id = fields.Many2one('bus.route.stop', related='bus_id.current_stop_id', string="Current Stop")
    bus_last_speed = fields.Float(related='bus_id.last_speed', string="Last Speed")
    bus_last_course = fields.Float(related='bus_id.last_course', string="Last Course")
    bus_last_latitude = fields.Float(related='bus_id.last_latitude', string="Latitude")
    bus_last_longitude = fields.Float(related='bus_id.last_longitude', string="Longitude")
    bus_traccar_unique_id = fields.Char(related='bus_id.traccar_unique_id', string="Traccar Unique ID")
    bus_demo_report = fields.Boolean(related='bus_id.demo_report', string="Demo report")
    bus_demo_report_until = fields.Datetime(related='bus_id.demo_report_until', string="Demo report until")
    bus_tablet_setup_link = fields.Char(related='bus_id.tablet_setup_link', string="Tablet setup link")
    bus_tablet_qr = fields.Binary(related='bus_id.tablet_qr', string="Tablet QR")
    bus_on_route = fields.Boolean(string="Driving a shift", readonly=True, copy=False)
    bus_service = fields.Selection(
        [('route', "On route"), ('parked', "Parked (not on route)"), ('retired', "Decommissioned")],
        string="Service", compute='_compute_bus_service', store=True, index=True, group_expand='_group_expand_service',
        help="On route while its bus drives a shift; decommissioned when archived or in the Downgraded state of Fleet.")

    @api.depends('active', 'state_id', 'bus_on_route')
    def _compute_bus_service(self):
        downgraded = self.env.ref('fleet.fleet_vehicle_state_downgraded', raise_if_not_found=False)
        for vehicle in self:
            if not vehicle.active or (downgraded and vehicle.state_id == downgraded):
                vehicle.bus_service = 'retired'
            elif vehicle.bus_on_route:
                vehicle.bus_service = 'route'
            else:
                vehicle.bus_service = 'parked'

    @api.model
    def _group_expand_service(self, values, domain, order):
        """The fleet board always shows its three columns, even an empty one."""
        return [key for key, _label in self._fields['bus_service'].selection]

    @api.depends('license_plate')
    def _compute_bus(self):
        buses = self.env['bus.vehicle'].sudo().with_context(active_test=False).search(
            [('fleet_vehicle_id', 'in', self.ids)])
        by_vehicle = {bus.fleet_vehicle_id.id: bus for bus in buses}
        for vehicle in self:
            vehicle.bus_id = by_vehicle.get(vehicle.id, False)

    def _search_bus_id(self, operator, value):
        buses = self.env['bus.vehicle'].sudo().with_context(active_test=False).search([('id', operator, value)])
        return [('id', 'in', buses.mapped('fleet_vehicle_id').ids)]

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get(SYNC) and TO_BUS.keys() & vals.keys():
            buses = self.env['bus.vehicle'].sudo().with_context(active_test=False).search(
                [('fleet_vehicle_id', 'in', self.ids)])
            for bus in buses:
                vehicle = bus.fleet_vehicle_id
                values = {TO_BUS[key]: (vehicle[key].id if key == 'driver_id' else vehicle[key])
                          for key in vals if key in TO_BUS}
                bus.with_context(**{SYNC: True}).write(values)
        return result

    def _ensure_bus(self):
        self.ensure_one()
        bus = self.bus_id
        if not bus:
            bus = self.env['bus.vehicle'].sudo().with_context(active_test=False).search(
                [('fleet_vehicle_id', '=', self.id)], limit=1)
            if not bus and self.license_plate:
                bus = self.env['bus.vehicle'].sudo().with_context(active_test=False).search(
                    [('plate', '=', self.license_plate)], limit=1)
            if not bus:
                bus = self.env['bus.vehicle'].with_context(**{SYNC: True}).create({
                    'name': self.name or f"Bus {self.license_plate or ''}",
                    'plate': self.license_plate or False,
                    'driver_id': self.driver_id.id if self.driver_id else False,
                    'capacity': self.seats or 30,
                    'fleet_vehicle_id': self.id,
                })
            else:
                bus.with_context(**{SYNC: True}).fleet_vehicle_id = self.id
            self.bus_id = bus
        return bus

    def action_open_bus(self):
        self.ensure_one()
        bus = self._ensure_bus()
        return {
            'type': 'ir.actions.act_window', 'name': _("Bus"), 'res_model': 'bus.vehicle',
            'res_id': bus.id, 'view_mode': 'form', 'target': 'current',
        }

    def action_register_gps(self):
        self.ensure_one()
        return self._ensure_bus().action_register_gps()

    def action_sync_now(self):
        self.ensure_one()
        return self._ensure_bus().action_sync_now()

    def action_open_map(self):
        self.ensure_one()
        return self._ensure_bus().action_open_map()

    def action_start_demo_report(self):
        self.ensure_one()
        return self._ensure_bus().action_start_demo_report()

    def action_stop_demo_report(self):
        self.ensure_one()
        return self._ensure_bus().action_stop_demo_report()


class BusShift(models.Model):
    _inherit = 'bus.shift'

    @api.model_create_multi
    def create(self, vals_list):
        shifts = super().create(vals_list)
        shifts.vehicle_id._sync_fleet_route()
        return shifts

    def write(self, vals):
        before = self.vehicle_id
        result = super().write(vals)
        if {'state', 'vehicle_id'} & vals.keys():
            (before | self.vehicle_id)._sync_fleet_route()
        return result

    def unlink(self):
        buses = self.vehicle_id
        result = super().unlink()
        buses.exists()._sync_fleet_route()
        return result
