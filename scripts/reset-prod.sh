#!/usr/bin/env bash
# Erase the production data and start again from nothing: Odoo database, its filestore and the
# Traccar database. Every bus, route, shift, position and complaint is lost.
#
#   scripts/reset-prod.sh            asks you to type the database name
#   CONFIRM=buses scripts/reset-prod.sh   (non-interactive, same check)
#
# It makes a backup first (scripts/backup.sh) and then runs scripts/init-prod.sh, which recreates
# everything with new random passwords shown once (Odoo admin, Traccar admin stored in Odoo) and sets
# the GPS address. No password is written in this file. Only for the local Postgres container
# (DB_HOST empty or "db"); with an external database (Supabase) reset it from its own console.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=.env.prod
DC="docker compose --env-file $ENV_FILE -f docker-compose.prod.yml"
[ -f "$ENV_FILE" ] || { echo "No $ENV_FILE here: run scripts/init-prod.sh first."; exit 1; }
set -a
. "./$ENV_FILE"
set +a
ODOO_DB="${ODOO_DB:-buses}"

case "${DB_HOST:-db}" in
  ""|db) ;;
  *) echo "DB_HOST=$DB_HOST is an external database: this script only resets the local container."; exit 1 ;;
esac

echo "This ERASES the production database '$ODOO_DB', its files and the Traccar database."
if [ "${CONFIRM:-}" != "$ODOO_DB" ]; then
  if [ ! -t 0 ]; then echo "Set CONFIRM=$ODOO_DB to run it without a terminal."; exit 1; fi
  printf "Type the database name (%s) to continue: " "$ODOO_DB"
  read -r answer
  [ "$answer" = "$ODOO_DB" ] || { echo "Cancelled."; exit 1; }
fi

echo "=== Backup first ==="
scripts/backup.sh

echo "=== Stopping Odoo and Traccar ==="
$DC stop odoo traccar

psql_admin() { $DC exec -T db psql -U odoo -d postgres -v ON_ERROR_STOP=1 "$@"; }
echo "=== Dropping the databases ==="
psql_admin -c "DROP DATABASE IF EXISTS \"$ODOO_DB\""
psql_admin -c "DROP DATABASE IF EXISTS traccar"

echo "=== Cleaning the filestore ==="
$DC run --rm -T --no-deps --entrypoint sh odoo -c "rm -rf /var/lib/odoo/filestore/$ODOO_DB"

echo "=== Recreating everything ==="
scripts/init-prod.sh
