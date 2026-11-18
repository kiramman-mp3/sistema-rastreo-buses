import logging

_logger = logging.getLogger(__name__)

# The read-only views Grafana read; the model that created them is gone.
KPI_VIEWS = [
    'kpi_alerts', 'kpi_positions', 'kpi_positions_daily', 'kpi_response', 'kpi_route_stops', 'kpi_routes',
    'kpi_software', 'kpi_trip_stops', 'kpi_trips',
]


def migrate(cr, version):
    """Grafana is no longer part of the system: drop its views, its settings and, when this user may, its role.
    The table of positions counted per day goes with its model when the update ends."""
    cr.execute(r"SELECT viewname FROM pg_views WHERE schemaname = 'public' AND viewname LIKE 'kpi\_%%'")
    for name in sorted({row[0] for row in cr.fetchall()} | set(KPI_VIEWS)):
        cr.execute('DROP VIEW IF EXISTS "%s" CASCADE' % name)
    cr.execute("DELETE FROM ir_config_parameter WHERE key LIKE 'bus_tracking.grafana%%'")
    cr.execute("SELECT 1 FROM pg_roles WHERE rolname = 'grafana_reader'")
    if cr.fetchone():
        cr.execute('SAVEPOINT drop_grafana_role')
        try:
            cr.execute('DROP OWNED BY grafana_reader')
            cr.execute('DROP ROLE grafana_reader')
            cr.execute('RELEASE SAVEPOINT drop_grafana_role')
        except Exception:  # noqa: BLE001 - the role may be used by another database, or this user may not drop roles
            cr.execute('ROLLBACK TO SAVEPOINT drop_grafana_role')
            _logger.warning("The database role grafana_reader is still there: drop it by hand if nothing uses it.")
