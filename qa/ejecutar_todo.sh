#!/bin/sh
# Full quality run from nothing (creates the database and the QA server if they are missing).
# Same as: python -X utf8 qa/ejecutar_todo.py [odoo|suite|auditoria|metricas ...] [--limpiar]
exec "${PYTHON:-python}" -X utf8 -u "$(dirname "$0")/ejecutar_todo.py" "$@"
