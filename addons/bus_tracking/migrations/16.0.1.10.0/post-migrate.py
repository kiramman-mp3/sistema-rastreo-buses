def migrate(cr, version):
    """The fine detector starts with this version: the alerts that already exist are history, not infractions to
    fine now (their positions may already be gone). Only the alerts from now on are looked at."""
    cr.execute("UPDATE bus_alert SET fine_checked = TRUE WHERE fine_checked IS NOT TRUE")
