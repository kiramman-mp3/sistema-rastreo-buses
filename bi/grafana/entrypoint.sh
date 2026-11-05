#!/bin/sh
# Grafana verifies the token that Odoo signs with a shared secret (HS256). Grafana wants that key as a JSON Web Key
# file; it is made here from the GRAFANA_JWT_SECRET variable so the secret never lives in the repository.
set -eu
: "${GRAFANA_JWT_SECRET:?set GRAFANA_JWT_SECRET}"
KEY="$(printf '%s' "$GRAFANA_JWT_SECRET" | base64 | tr -d '\n=' | tr '+/' '-_')"
printf '{"keys":[{"kty":"oct","alg":"HS256","use":"sig","kid":"odoo","k":"%s"}]}' "$KEY" > /tmp/jwks.json
exec /run.sh "$@"
