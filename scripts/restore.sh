#!/usr/bin/env bash
# Restores a backup made by scripts/backup.sh.
#
#   scripts/restore.sh backups/<stamp> --target-db buses_check
#       Restores only the Odoo database under another name, leaving production untouched.
#       Use it to prove a backup is usable.
#
#   scripts/restore.sh backups/<stamp> --yes
#       Replaces the production Odoo and Traccar databases and the filestore. DESTRUCTIVE.
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP="${1:-}"
[ -n "$BACKUP" ] && [ -d "$BACKUP" ] || { echo "Usage: $0 backups/<stamp> [--target-db NAME | --yes]"; exit 1; }
shift

ENV_FILE=.env.prod
DC="docker compose --env-file $ENV_FILE -f docker-compose.prod.yml"
set -a
. "./$ENV_FILE"
set +a
ODOO_DB="${ODOO_DB:-buses}"

TARGET=""
CONFIRMED=0
while [ $# -gt 0 ]; do
  case "$1" in
    --target-db) TARGET="$2"; shift 2 ;;
    --yes) CONFIRMED=1; shift ;;
    *) echo "Unknown option $1"; exit 1 ;;
  esac
done

(cd "$BACKUP" && sha256sum -c SHA256SUMS)

psql_admin() { $DC exec -T db psql -U odoo -d postgres -v ON_ERROR_STOP=1 "$@"; }

if [ -n "$TARGET" ]; then
  [ "$TARGET" != "$ODOO_DB" ] || { echo "--target-db must differ from the production database ($ODOO_DB)."; exit 1; }
  echo "Restoring Odoo database into '$TARGET' (production is not touched)..."
  psql_admin -c "DROP DATABASE IF EXISTS \"$TARGET\""
  psql_admin -c "CREATE DATABASE \"$TARGET\" OWNER odoo"
  $DC exec -T db pg_restore -U odoo -d "$TARGET" --no-owner < "$BACKUP/odoo.dump"
  echo "Done. Inspect it with: docker compose --env-file $ENV_FILE -f docker-compose.prod.yml exec db psql -U odoo -d $TARGET"
  exit 0
fi

if [ "$CONFIRMED" != 1 ]; then
  echo "This replaces the production databases '$ODOO_DB' and 'traccar' and the filestore with $BACKUP."
  echo "Run again with --yes to proceed."
  exit 1
fi

echo "Stopping Odoo and Traccar..."
$DC stop odoo traccar
psql_admin -c "DROP DATABASE IF EXISTS \"$ODOO_DB\""
psql_admin -c "CREATE DATABASE \"$ODOO_DB\" OWNER odoo"
$DC exec -T db pg_restore -U odoo -d "$ODOO_DB" --no-owner < "$BACKUP/odoo.dump"

psql_admin -c "DROP DATABASE IF EXISTS traccar"
psql_admin -c "CREATE DATABASE traccar OWNER traccar"
$DC exec -T db pg_restore -U odoo -d traccar --no-owner --role=traccar < "$BACKUP/traccar.dump"

echo "Restoring filestore..."
$DC run --rm -T --no-deps --entrypoint sh odoo -c "rm -rf /var/lib/odoo/filestore/$ODOO_DB && mkdir -p /var/lib/odoo/filestore/$ODOO_DB && tar xzf - -C /var/lib/odoo/filestore/$ODOO_DB" < "$BACKUP/filestore.tgz"

$DC up -d
echo "Restore complete."
