"""Incidents gained `reported_at` (when the driver pressed the button). For the old ones it is
the time they reached Odoo."""


def migrate(cr, version):
    cr.execute("UPDATE bus_incident SET reported_at = create_date")
