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
                vehicle = Fleet.create(dict(bus._fleet_values(), model_id=bus._fleet_model().id))
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

    bus_id = fields.Many2one('bus.vehicle', string="Tracked as bus", compute='_compute_bus', compute_sudo=True)
    bus_traccar_device_id = fields.Integer(string="GPS device (Traccar)", related='bus_id.traccar_device_id')
    bus_connection = fields.Selection(related='bus_id.connection', string="GPS connection")
    bus_last_fix_time = fields.Datetime(related='bus_id.last_fix_time', string="Last position")

    @api.depends('license_plate')
    def _compute_bus(self):
        buses = self.env['bus.vehicle'].sudo().with_context(active_test=False).search(
            [('fleet_vehicle_id', 'in', self.ids)])
        by_vehicle = {bus.fleet_vehicle_id.id: bus for bus in buses}
        for vehicle in self:
            vehicle.bus_id = by_vehicle.get(vehicle.id, False)

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

    def action_open_bus(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _("Bus"), 'res_model': 'bus.vehicle',
            'res_id': self.bus_id.id, 'view_mode': 'form', 'target': 'current',
        }
