#!/usr/bin/env bash
# Creates (or updates the password of) the read-only database role Grafana uses: it reads the kpi_* views of Odoo and
# nothing else. Run it after the module is installed or updated, as a database superuser.
#
#   GRAFANA_DB_PASSWORD=... ODOO_DB=buses scripts/grafana-role.sh                      # development stack
#   GRAFANA_DB_PASSWORD=... ODOO_DB=buses PSQL="psql postgres://admin@host/postgres" scripts/grafana-role.sh
#
# With DB_HOST set to an external server (Supabase, as init-prod.sh does from .env.prod) it connects there with
# DB_USER and DB_PASSWORD from a throwaway client container; otherwise it runs psql inside the "db" service of the
# docker compose file in the current folder.
set -euo pipefail

: "${GRAFANA_DB_PASSWORD:?set GRAFANA_DB_PASSWORD}"
DB="${ODOO_DB:-buses}"
case "$GRAFANA_DB_PASSWORD" in *\'*|*\*) echo "The password must not contain ' or \\" >&2; exit 1;; esac
case "$DB" in *\"*) echo "The database name must not contain a double quote" >&2; exit 1;; esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Plain text replacement, not sed: a / or & in the password must not change the SQL.
SQL="$(PW="$GRAFANA_DB_PASSWORD" DBN="$DB" awk '{
    while ((i = index($0, "__PASSWORD__")) > 0) $0 = substr($0, 1, i - 1) ENVIRON["PW"] substr($0, i + 12)
    while ((i = index($0, "__DB__")) > 0) $0 = substr($0, 1, i - 1) ENVIRON["DBN"] substr($0, i + 6)
    print
}' "$HERE/addons/bus_tracking/data/grafana-role.sql")"

if [ -n "${PSQL:-}" ]; then
    # shellcheck disable=SC2086
    printf '%s\n' "$SQL" | $PSQL -v ON_ERROR_STOP=1 -d "$DB"
elif [ -n "${DB_HOST:-}" ] && [ "$DB_HOST" != "db" ]; then
    printf '%s\n' "$SQL" | docker run --rm -i -e PGPASSWORD="${DB_PASSWORD:?set DB_PASSWORD}" -e PGSSLMODE=require \
        "${POSTGRES_IMAGE:-postgres:15}" psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "${DB_PORT:-5432}" \
        -U "${DB_USER:?set DB_USER}" -d "$DB"
else
    COMPOSE="${COMPOSE:-docker compose}"
    # shellcheck disable=SC2086
    printf '%s\n' "$SQL" | $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "${DB_USER:-odoo}" -d "$DB"
fi
echo "Role grafana_reader ready on database $DB."
