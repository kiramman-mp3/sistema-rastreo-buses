from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The fleet board puts a vehicle in On route while its bus drives a shift: mark the ones driving now."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['bus.vehicle'].with_context(active_test=False).search([('fleet_vehicle_id', '!=', False)])._sync_fleet_route()
