-- The database role Grafana connects with. It can read the kpi_* views and nothing else: no table of Odoo,
-- no user, no password hash, no way to write. Run it as a superuser with the tokens replaced
-- (scripts/grafana-role.sh does it): __PASSWORD__ is the password of the role and __DB__ the database of Odoo.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'grafana_reader') THEN
        CREATE ROLE grafana_reader LOGIN PASSWORD '__PASSWORD__' CONNECTION LIMIT 5
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    ELSE
        ALTER ROLE grafana_reader LOGIN PASSWORD '__PASSWORD__' CONNECTION LIMIT 5;
    END IF;
END
$$;

ALTER ROLE grafana_reader SET default_transaction_read_only = on;
ALTER ROLE grafana_reader SET statement_timeout = '10s';
ALTER ROLE grafana_reader SET idle_in_transaction_session_timeout = '30s';

GRANT CONNECT ON DATABASE "__DB__" TO grafana_reader;
GRANT USAGE ON SCHEMA public TO grafana_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM grafana_reader;
GRANT SELECT ON kpi_routes, kpi_route_stops, kpi_trips, kpi_trip_stops, kpi_alerts, kpi_positions,
    kpi_positions_daily, kpi_response, kpi_software TO grafana_reader;
