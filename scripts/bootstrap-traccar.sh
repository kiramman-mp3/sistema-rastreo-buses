#!/usr/bin/env bash
# For a Traccar reinstalled on its own, when Odoo lost its credentials: creates another Traccar administrator
# with a random password, stores an API token for it in Odoo (not the password) and closes self-registration.
# Does nothing when Odoo already has credentials.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=.env.prod
DC="docker compose --env-file $ENV_FILE -f docker-compose.prod.yml"
set -a
. "./$ENV_FILE"
set +a
ODOO_DB="${ODOO_DB:-buses}"

TRACCAR_ADMIN_PASSWORD=$(head -c 96 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)
$DC run --rm -T -e BOOT_EMAIL="admin@$DOMAIN" -e BOOT_PASSWORD="$TRACCAR_ADMIN_PASSWORD" odoo odoo shell -d "$ODOO_DB" --log-level=error <<'PYEOF'
import os
api = env['bus.traccar.api']
if api.bootstrap_admin(os.environ['BOOT_EMAIL'], os.environ['BOOT_PASSWORD']):
    print("TRACCAR_BOOTSTRAP_SUCCESS")
else:
    print("TRACCAR_ALREADY_CONFIGURED")
env.cr.commit()
PYEOF
