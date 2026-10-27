#!/usr/bin/env bash
# First-time production setup: secrets, Odoo config, databases, module install.
# Safe to re-run: it never overwrites an existing .env.prod, config or database.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=.env.prod
CONF=config/odoo.prod.conf
DC="docker compose --env-file $ENV_FILE -f docker-compose.prod.yml"

rand() { head -c 96 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c "${1:-32}"; }

if [ ! -f "$ENV_FILE" ]; then
  cp .env.prod.example "$ENV_FILE"
  for key in DB_PASSWORD TRACCAR_DB_PASSWORD WEBHOOK_SECRET; do
    sed -i "s|^$key=CHANGE_ME|$key=$(rand 40)|" "$ENV_FILE"
  done
  echo "Created $ENV_FILE with random secrets."
  echo "Edit DOMAIN, GPS_DOMAIN and ACME_EMAIL in it, then run this script again."
  exit 0
fi

set -a
. "./$ENV_FILE"
set +a

case "$DOMAIN" in
  *example.com) echo "Set a real DOMAIN, GPS_DOMAIN and ACME_EMAIL in $ENV_FILE first."; exit 1 ;;
esac

ODOO_DB="${ODOO_DB:-buses}"
ODOO_LANG="${ODOO_LANG:-}"

if [ ! -f "$CONF" ]; then
  MASTER_PASSWORD=$(rand 28)
  MASTER_HASH=$(docker run --rm --entrypoint python3 "${ODOO_IMAGE:-odoo:16.0}" -c "from passlib.hash import pbkdf2_sha512; print(pbkdf2_sha512.hash('$MASTER_PASSWORD'))")
  cat > "$CONF" <<EOF
[options]
admin_passwd = $MASTER_HASH
db_name = $ODOO_DB
dbfilter = ^$ODOO_DB\$
list_db = False
proxy_mode = True
data_dir = /var/lib/odoo
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
workers = 2
max_cron_threads = 1
limit_memory_soft = 1073741824
limit_memory_hard = 1342177280
limit_time_cpu = 120
limit_time_real = 240
log_level = info
EOF
  echo "Created $CONF. Odoo master password (shown once, store it in a password manager): $MASTER_PASSWORD"
fi

$DC up -d db
echo "Waiting for Postgres..."
until $DC exec -T db pg_isready -U odoo -d postgres >/dev/null 2>&1; do sleep 2; done

psql_admin() { $DC exec -T db psql -U odoo -d postgres -v ON_ERROR_STOP=1 "$@"; }

if [ -z "$(psql_admin -tAc "SELECT 1 FROM pg_roles WHERE rolname='traccar'")" ]; then
  psql_admin -c "CREATE ROLE traccar LOGIN PASSWORD '$TRACCAR_DB_PASSWORD'"
fi
if [ -z "$(psql_admin -tAc "SELECT 1 FROM pg_database WHERE datname='traccar'")" ]; then
  psql_admin -c "CREATE DATABASE traccar OWNER traccar"
fi

if [ -z "$(psql_admin -tAc "SELECT 1 FROM pg_database WHERE datname='$ODOO_DB'")" ]; then
  INSTALL_ARGS="-d $ODOO_DB -i bus_tracking --stop-after-init --without-demo=all"
  if [ -n "$ODOO_LANG" ]; then INSTALL_ARGS="$INSTALL_ARGS --load-language=$ODOO_LANG"; fi
  $DC run --rm -T odoo odoo $INSTALL_ARGS
  ADMIN_PASSWORD=$(rand 20)
  $DC run --rm -T -e NEW_ADMIN_PASSWORD="$ADMIN_PASSWORD" -e WEBHOOK_SECRET="$WEBHOOK_SECRET" -e ODOO_LANG="$ODOO_LANG" odoo odoo shell -d "$ODOO_DB" --log-level=error <<'EOF'
import os
admin = env.ref('base.user_admin')
admin.password = os.environ['NEW_ADMIN_PASSWORD']
admin.tz = 'America/Guayaquil'
env.company.partner_id.tz = 'America/Guayaquil'
if os.environ.get('ODOO_LANG'):
    admin.lang = os.environ['ODOO_LANG']
icp = env['ir.config_parameter']
icp.set_param('bus_tracking.webhook_secret', os.environ['WEBHOOK_SECRET'])
icp.set_param('bus_tracking.traccar_url', 'http://traccar:8082')
env.cr.commit()
EOF
  echo "Odoo user 'admin' password (shown once): $ADMIN_PASSWORD"
fi

$DC up -d

echo "Waiting for Traccar..."
until $DC ps traccar --format '{{.Status}}' | grep -q healthy; do sleep 3; done

# Odoo creates the Traccar administrator (random password, stored in Odoo) and closes self-registration,
# so nobody has to touch Traccar's own panel.
TRACCAR_ADMIN_PASSWORD=$(rand 24)
$DC run --rm -T -e BOOT_EMAIL="admin@$DOMAIN" -e BOOT_PASSWORD="$TRACCAR_ADMIN_PASSWORD" -e GPS_URL="https://$GPS_DOMAIN" odoo odoo shell -d "$ODOO_DB" --log-level=error <<'EOF'
import os
created = env['bus.traccar.api'].bootstrap_admin(os.environ['BOOT_EMAIL'], os.environ['BOOT_PASSWORD'])
env['ir.config_parameter'].set_param('bus_tracking.gps_url', os.environ['GPS_URL'])
env.cr.commit()
print('TRACCAR_BOOTSTRAP', 'created' if created else 'already configured')
EOF

echo
echo "Stack is up. Next:"
echo "  1. Open https://$DOMAIN and sign in as admin with the password shown above."
echo "  2. Create your routes and stops, and one bus per driver's phone."
echo "  3. On each bus press 'Register GPS in Traccar' and follow the 'Driver's phone' section (docs/GUIA-CHOFER.md)."
echo "  4. Schedule scripts/backup.sh (see docs/PRODUCCION.md)."
