"""Drivers used to be internal users, so they could open the Odoo backend with their tablet
password. Turn the ones that only drive into portal users; anyone who is also staff
(Bus Tracking User or Manager) keeps an internal account."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    driver = env.ref('bus_tracking.group_bus_driver', raise_if_not_found=False)
    staff = env.ref('bus_tracking.group_bus_user', raise_if_not_found=False)
    portal = env.ref('base.group_portal', raise_if_not_found=False)
    if not (driver and staff and portal):
        return
    keep = {env.ref('base.user_root').id, env.ref('base.user_admin').id}
    drivers = env['res.users'].with_context(active_test=False).search([
        ('groups_id', 'in', driver.ids),
        ('groups_id', 'not in', staff.ids),
        ('share', '=', False),
        ('id', 'not in', list(keep)),
    ])
    drivers.write({'groups_id': [(6, 0, [portal.id, driver.id])]})
