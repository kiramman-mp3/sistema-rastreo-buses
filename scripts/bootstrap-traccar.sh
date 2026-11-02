#!/usr/bin/env bash
set -euo pipefail
cd /home/azureuser/buses
set -a
. ./.env.prod
set +a
TRACCAR_ADMIN_PASSWORD=$(head -c 96 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm -T -e BOOT_EMAIL="admin@$DOMAIN" -e BOOT_PASSWORD="$TRACCAR_ADMIN_PASSWORD" odoo odoo shell -d buses --log-level=error <<'PYEOF'
import os
api = env['bus.traccar.api']
if api.bootstrap_admin(os.environ['BOOT_EMAIL'], os.environ['BOOT_PASSWORD']):
    print("TRACCAR_BOOTSTRAP_SUCCESS")
else:
    print("TRACCAR_ALREADY_CONFIGURED")
env.cr.commit()
PYEOF
docker compose --env-file .env.prod -f docker-compose.prod.yml restart proxy
