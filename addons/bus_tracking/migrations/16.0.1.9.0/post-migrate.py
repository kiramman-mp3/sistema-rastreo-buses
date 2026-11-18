from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The fleet board puts a vehicle in On route while its bus drives a shift: mark the ones driving now.

    This version also renames menus (Indicators to Reports, Reports to Notifications). An update without
    --i18n-overwrite keeps the translations already in the database, so the Spanish and Kichwa menus would keep
    their old names: reload the terms of this module over them."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['bus.vehicle'].with_context(active_test=False).search([('fleet_vehicle_id', '!=', False)])._sync_fleet_route()
    env['ir.module.module'].search([('name', '=', 'bus_tracking')])._update_translations(overwrite=True)
