"""Odoo Fleet joins the module: every bus of the company that is already registered gets its vehicle in Fleet
(the one that already has its plate, or a new one). Safe to run twice."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['bus.vehicle'].with_context(active_test=False).search([])._link_fleet()
