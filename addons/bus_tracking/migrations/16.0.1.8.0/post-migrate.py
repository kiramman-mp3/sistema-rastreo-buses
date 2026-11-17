import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """The QR badge is no longer stored (S1): its link and image held the raw token. Delete them, and revoke the
    badges they belong to, since any backup taken before still holds them. Drivers need a new printed badge."""
    cr.execute("DELETE FROM ir_attachment WHERE res_model = 'res.users' AND res_field = 'driver_badge_qr'")
    cr.execute("ALTER TABLE res_users DROP COLUMN IF EXISTS driver_badge_link")
    cr.execute("ALTER TABLE res_users DROP COLUMN IF EXISTS driver_badge_qr")
    cr.execute("DELETE FROM bus_driver_token WHERE device_label = 'badge_qr'")
    if cr.rowcount:
        _logger.warning("Revoked %d QR badges: generate and print a new badge for each driver.", cr.rowcount)
