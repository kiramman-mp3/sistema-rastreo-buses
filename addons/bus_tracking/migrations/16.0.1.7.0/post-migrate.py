"""Swap the stored Traccar administrator password for a long-lived API token, so a copy of the database no
longer holds the password. When Traccar does not answer, everything stays as it was: the swap can be done
later from an Odoo shell with env['bus.traccar.api'].switch_to_token()."""
import logging

from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        if env['bus.traccar.api'].switch_to_token():
            _logger.info("Traccar: the administrator password was replaced by an API token.")
    except UserError as error:
        _logger.warning("Traccar: kept the stored password, no token was obtained: %s", error)
