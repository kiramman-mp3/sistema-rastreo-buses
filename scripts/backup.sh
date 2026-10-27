#!/usr/bin/env bash
# Backs up the Odoo database, the Odoo filestore and the Traccar database into backups/<timestamp>/.
# Secrets (.env.prod, config/odoo.prod.conf) are NOT included: keep them in a password manager.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=.env.prod
DC="docker compose --env-file $ENV_FILE -f docker-compose.prod.yml"
set -a
. "./$ENV_FILE"
set +a
ODOO_DB="${ODOO_DB:-buses}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="backups/$STAMP"
mkdir -p "$OUT"

echo "Dumping Odoo database $ODOO_DB..."
$DC exec -T db pg_dump -U odoo -Fc "$ODOO_DB" > "$OUT/odoo.dump"

echo "Dumping Traccar database..."
$DC exec -T db pg_dump -U odoo -Fc traccar > "$OUT/traccar.dump"

echo "Archiving Odoo filestore..."
$DC exec -T odoo sh -c "if [ -d /var/lib/odoo/filestore/$ODOO_DB ]; then tar czf - -C /var/lib/odoo/filestore/$ODOO_DB .; else tar czf - -T /dev/null; fi" > "$OUT/filestore.tgz"

(cd "$OUT" && sha256sum odoo.dump traccar.dump filestore.tgz > SHA256SUMS)

# Remove only timestamped folders older than the retention window.
find backups -mindepth 1 -maxdepth 1 -type d -name '20*' -mtime +"$KEEP_DAYS" -exec rm -rf {} +

echo "Backup written to $OUT"
ls -l "$OUT"
