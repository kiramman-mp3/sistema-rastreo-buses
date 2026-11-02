#!/usr/bin/env bash
set -euo pipefail

echo "=== Step 1: Syncing latest code from main branch ==="
cd /tmp
rm -rf deploy-repo
git clone -b main --single-branch https://github.com/kiramman-mp3/sistema-rastreo-buses.git deploy-repo
cp -r deploy-repo/addons/bus_tracking /home/azureuser/buses/addons/
cp deploy-repo/proxy/Caddyfile /home/azureuser/buses/proxy/
rm -rf deploy-repo
echo "Code synced successfully."

echo "=== Step 2: Stopping Odoo and Traccar ==="
docker stop rastreo-prod-odoo-1 rastreo-prod-traccar-1 || true

echo "=== Step 3: Dropping and recreating clean databases ==="
docker exec rastreo-prod-db-1 psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS buses;"
docker exec rastreo-prod-db-1 psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS traccar;"
docker exec rastreo-prod-db-1 psql -U odoo -d postgres -c "CREATE DATABASE traccar OWNER traccar;"

cd /home/azureuser/buses
set -a
. ./.env.prod
set +a

echo "=== Step 4: Cleaning filestore ==="
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm -T --no-deps --entrypoint sh odoo -c "rm -rf /var/lib/odoo/filestore/buses" || true

echo "=== Step 5: Initializing fresh Odoo database with bus_tracking ==="
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm -T odoo odoo -d buses -i bus_tracking --stop-after-init --without-demo=all

echo "=== Step 6: Configuring admin user and parameters ==="
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm -T -e NEW_ADMIN_PASSWORD="zUjU9n39HlR0b6d2kQcW" -e WEBHOOK_SECRET="$WEBHOOK_SECRET" odoo odoo shell -d buses --log-level=error <<'PYEOF'
import os
admin = env.ref('base.user_admin')
admin.password = os.environ['NEW_ADMIN_PASSWORD']
admin.tz = 'America/Guayaquil'
env.company.partner_id.tz = 'America/Guayaquil'
icp = env['ir.config_parameter']
icp.set_param('bus_tracking.webhook_secret', os.environ['WEBHOOK_SECRET'])
icp.set_param('bus_tracking.traccar_url', 'http://traccar:8082')
env.cr.commit()
print('Odoo parameters initialized successfully.')
PYEOF

echo "=== Step 7: Starting all services ==="
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d

echo "=== Step 8: Configuring Traccar ==="
until docker compose --env-file .env.prod -f docker-compose.prod.yml ps traccar --format '{{.Status}}' | grep -q healthy; do sleep 3; done
TRACCAR_ADMIN_PASSWORD=$(head -c 96 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm -T -e BOOT_EMAIL="admin@$DOMAIN" -e BOOT_PASSWORD="$TRACCAR_ADMIN_PASSWORD" -e GPS_URL="https://$GPS_DOMAIN" odoo odoo shell -d buses --log-level=error <<'PYEOF'
import os
api = env['bus.traccar.api']
api.setup_server(os.environ['GPS_URL'])
api.setup_admin_user(os.environ['BOOT_EMAIL'], os.environ['BOOT_PASSWORD'])
api.disable_registration()
env.cr.commit()
print('Traccar admin initialized successfully.')
PYEOF

echo "=== Step 9: Reloading Caddy proxy ==="
docker compose --env-file .env.prod -f docker-compose.prod.yml restart proxy

echo "=== DATABASE CLEAN COMPLETE ==="
