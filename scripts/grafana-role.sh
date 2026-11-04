#!/usr/bin/env bash
# Creates (or updates the password of) the read-only database role Grafana uses: it reads the kpi_* views of Odoo and
# nothing else. Run it after the module is installed or updated, as a database superuser.
#
#   GRAFANA_DB_PASSWORD=... ODOO_DB=buses scripts/grafana-role.sh                      # development stack
#   GRAFANA_DB_PASSWORD=... ODOO_DB=buses PSQL="psql postgres://admin@host/postgres" scripts/grafana-role.sh
#
# By default it runs psql inside the "db" service of the docker compose file in the current folder.
set -euo pipefail

: "${GRAFANA_DB_PASSWORD:?set GRAFANA_DB_PASSWORD}"
DB="${ODOO_DB:-buses}"
case "$GRAFANA_DB_PASSWORD" in *\'*|*\*) echo "The password must not contain ' or \\" >&2; exit 1;; esac
case "$DB" in *\"*) echo "The database name must not contain a double quote" >&2; exit 1;; esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL="$(sed -e "s/__PASSWORD__/${GRAFANA_DB_PASSWORD}/g" -e "s/__DB__/${DB}/g" "$HERE/addons/bus_tracking/data/grafana-role.sql")"

if [ -n "${PSQL:-}" ]; then
    # shellcheck disable=SC2086
    printf '%s\n' "$SQL" | $PSQL -v ON_ERROR_STOP=1 -d "$DB"
else
    COMPOSE="${COMPOSE:-docker compose}"
    # shellcheck disable=SC2086
    printf '%s\n' "$SQL" | $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -U "${DB_USER:-odoo}" -d "$DB"
fi
echo "Role grafana_reader ready on database $DB."
