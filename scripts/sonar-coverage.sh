#!/usr/bin/env bash
# Coverage reports that SonarQube reads:
#   coverage.xml                              the Odoo module (the tests run under coverage.py, in a database that is dropped)
#   apps/conductor-tablet/coverage/lcov.info  the driver app (Jest)
# The development stack must be up (docker compose up -d db). Takes a few minutes.
set -euo pipefail
cd "$(dirname "$0")/.."

DB=buses_cov
REPO="$(pwd -W 2>/dev/null || pwd)"
NETWORK="${COMPOSE_NETWORK:-$(basename "$PWD")_default}"
export MSYS_NO_PATHCONV=1

echo "==> Odoo tests under coverage (database $DB)"
docker compose exec -T db dropdb -U odoo --if-exists "$DB" >/dev/null
mkdir -p .sonar-out
docker run --rm --network "$NETWORK" -e HOST=db -e USER=odoo -e PASSWORD=odoo \
  -v "$REPO/addons:/mnt/extra-addons:ro" -v "$REPO/bi:/mnt/bi:ro" -v "$REPO/.sonar-out:/out" \
  rastreo-odoo:16.0 sh -c '
    pip3 install -q coverage &&
    python3 -m coverage run --branch --data-file=/tmp/.coverage --source=/mnt/extra-addons/bus_tracking --omit="*/tests/*" \
      /usr/bin/odoo -d '"$DB"' --db_host $HOST --db_user $USER --db_password $PASSWORD -i bus_tracking \
      --test-enable --test-tags /bus_tracking --stop-after-init --without-demo=all --no-http > /out/odoo_test.log 2>&1;
    python3 -m coverage xml --data-file=/tmp/.coverage -o /out/coverage.xml -q'
docker compose exec -T db dropdb -U odoo --if-exists "$DB" >/dev/null
grep -E "odoo.tests.result" .sonar-out/odoo_test.log | tail -1

# SonarQube wants the paths from the project root, not from the source folder of coverage.py.
sed -E 's#filename="mnt/extra-addons/#filename="addons/#; s#<source>[^<]*</source>#<source>.</source>#' \
  .sonar-out/coverage.xml > coverage.xml
echo "coverage.xml written"

echo "==> Jest coverage (driver app)"
(cd apps/conductor-tablet && npx jest --coverage --coverageReporters=lcov --coverageReporters=text-summary 2>&1 | tail -12)
