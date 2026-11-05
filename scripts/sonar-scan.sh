#!/usr/bin/env bash
# Analyses the project with SonarQube (development): coverage, then sonar-scanner in a container.
#
#   docker compose -f docker-compose.sonar.yml up -d           # wait for http://localhost:9000
#   SONAR_TOKEN=<project analysis token> scripts/sonar-scan.sh
#
# SKIP_COVERAGE=1 reuses the reports of the last run. The result is read in the SonarQube web page or with
#   curl -u "$SONAR_TOKEN:" "http://localhost:9000/api/qualitygates/project_status?projectKey=sistema-rastreo-buses"
set -euo pipefail
cd "$(dirname "$0")/.."

: "${SONAR_TOKEN:?set SONAR_TOKEN (SonarQube > My Account > Security > Generate a token)}"
REPO="$(pwd -W 2>/dev/null || pwd)"
export MSYS_NO_PATHCONV=1

if [ "${SKIP_COVERAGE:-0}" != "1" ]; then
  scripts/sonar-coverage.sh
fi

echo "==> sonar-scanner"
docker run --rm --network rastreo-sonar_default \
  -e SONAR_HOST_URL="${SONAR_HOST_URL:-http://sonarqube:9000}" -e SONAR_TOKEN \
  -v "$REPO:/usr/src" sonarsource/sonar-scanner-cli:latest "$@"
