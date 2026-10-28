#!/bin/sh
# Full quality run: restart the QA server (clean in-memory limits), live suite, audit and metrics.
# Needs the QA stack: docker compose up -d db, a database "buses_qa" with bus_tracking installed and the container "qa-odoo"
# (see Anexo B of the report).
set -e
cd "$(dirname "$0")/.."
docker restart qa-odoo >/dev/null
sleep 15
python -X utf8 -u qa/qa_suite.py > docs/calidad/evidencias/suite.log 2>&1 || true
python -X utf8 -u qa/auditoria.py > docs/calidad/evidencias/auditoria.log 2>&1
python -X utf8 -u qa/metricas.py > docs/calidad/evidencias/metricas.log 2>&1
