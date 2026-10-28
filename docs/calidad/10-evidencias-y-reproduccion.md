# Evidencias y cómo repetir las pruebas

## 1. Evidencias que se guardan por entrega

Por cada versión candidata a pasar a `main` se conservan estos artefactos (los del taller de referencia, más los propios del proyecto):

| N.º | Evidencia | Archivo | Qué demuestra |
|---|---|---|---|
| 1 | Registro de las pruebas de Odoo | `evidencias/odoo_test.log` | 150 pruebas, 0 fallos, tiempo de cada una |
| 2 | Cobertura de código | `evidencias/cobertura.txt`, `evidencias/coverage.json` | Sentencias y ramas cubiertas por archivo |
| 3 | Resultado de la suite en vivo | `evidencias/suite.json`, `evidencias/suite.log` | 42 casos con entrada, resultado, mensaje, estado y tiempo |
| 4 | Resultado de la auditoría aleatoria | `evidencias/auditoria.json`, `evidencias/auditoria.log` | 1000 peticiones con semilla fija, errores por causa y tiempos |
| 5 | Métricas y estado de los datos | `evidencias/metricas.json`, `evidencias/metricas.log` | Error, tiempos, cobertura, líneas de código y consultas SQL |
| 6 | Registro de defectos | `05-registro-de-defectos.md` | Defectos con causa raíz y estado |
| 7 | Reporte de análisis estático | (pendiente) | SonarQube, flake8 y pylint-odoo: aún no están configurados |
| 8 | Informe técnico | `Informe_calidad_rastreo_buses.pdf` | Resumen firmado para el curso |

Las figuras de los informes están en `figuras/`.

## 2. Lista de comprobación antes de integrar

- [ ] Las pruebas de Odoo pasan al 100 % en una base nueva.
- [ ] La suite en vivo no tiene respuestas 5xx ni registros inválidos.
- [ ] La auditoría aleatoria no supera el 10 % de error.
- [ ] La cobertura no baja de 80 %.
- [ ] Cada defecto corregido tiene su prueba nueva.
- [ ] `05-registro-de-defectos.md` y `docs/BITACORA.md` están al día.
- [ ] Las evidencias de la tabla anterior se regeneraron para esta versión.

## 3. Entorno de pruebas

- Windows con Docker Desktop y Git Bash; Python 3.13 en el equipo con `requests`, `matplotlib`, `reportlab` y `pymupdf` (solo para el informe).
- Odoo 16 (imagen `rastreo-odoo:16.0`) y Postgres 15 del `docker-compose.yml`.
- Una base nueva `buses_qa` con el módulo instalado y **sin** el español cargado.
- Un servidor Odoo dedicado `qa-odoo` en el puerto 8071, con filtro de base `^buses_qa$`.
- Contraseña del administrador `admin`/`admin` (la que Odoo crea en una base nueva sin datos de demostración).

Dos límites del sistema viven en la memoria del proceso (60 consultas por minuto del feed y 5 quejas por hora). Por eso `qa/ejecutar_todo.sh` reinicia `qa-odoo` antes de empezar, y la suite espera 61 segundos antes de probar el límite del feed.

## 4. Procedimiento

```bash
# 1. Servicios
cp .env.example .env            # una sola vez; cambia DB_PASSWORD y WEBHOOK_SECRET
docker compose up -d db

# 2. Pruebas de Odoo con cobertura (base nueva buses_qa)
SP="C:\ruta\a\una\carpeta\vacia"
MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps --user root -v "$SP:/out" -w /out odoo sh -c '
  pip3 install -q coverage
  coverage run --branch --data-file=/out/.coverage --source=/mnt/extra-addons/bus_tracking --omit="*/tests/*" \
    /usr/bin/odoo -d buses_qa --db_host $HOST --db_user $USER --db_password $PASSWORD -i bus_tracking \
    --test-enable --test-tags /bus_tracking --stop-after-init --without-demo=all --log-level=test > /out/odoo_test.log 2>&1
  coverage report --data-file=/out/.coverage -m > /out/coverage_report.txt
  coverage json --data-file=/out/.coverage -o /out/coverage.json -q'
# copiar odoo_test.log, coverage.json y coverage_report.txt (como cobertura.txt) a docs/calidad/evidencias/

# 3. Servidor dedicado para las pruebas en vivo
MSYS_NO_PATHCONV=1 docker compose run -d --no-deps --name qa-odoo -p 8071:8069 odoo \
  odoo -d buses_qa --db-filter '^buses_qa$'

# 4. Suite en vivo, auditoría y métricas (reinicia qa-odoo al empezar)
sh qa/ejecutar_todo.sh

# 5. Documentos y figuras
python -X utf8 qa/generar_docs.py        # 03, 04, 05, 07 y las figuras de Pareto e Ishikawa
python -X utf8 qa/generar_informe.py     # informe en PDF

# 6. Limpieza
docker rm -f qa-odoo
docker exec <contenedor-db> psql -U odoo -d postgres -c "DROP DATABASE buses_qa"
```

Variables útiles: `QA_BASE`, `QA_DB`, `QA_ADMIN_LOGIN`, `QA_ADMIN_PASSWORD` y `QA_OUT` (carpeta de salida) cambian el servidor y los archivos que usa `qa/`.

## 5. Qué hace cada script

| Script | Función |
|---|---|
| `qa/common.py` | Conexión XML-RPC, datos de prueba (ruta, 45 buses, secreto), estadísticas y consultas SQL |
| `qa/qa_suite.py` | 42 casos en vivo (F, E, P y U) |
| `qa/auditoria.py` | 1000 peticiones aleatorias sobre 15 áreas, semilla 20261028 |
| `qa/metricas.py` | Métricas desde las evidencias, cobertura de rutas, líneas de código y consultas SQL |
| `qa/ejecutar_todo.sh` | Reinicia el servidor y ejecuta suite, auditoría y métricas |
| `qa/datos_calidad.py` | Defectos y problemas de la bitácora clasificados |
| `qa/generar_docs.py` | Documentos 03, 04, 05 y 07 y las figuras |
| `qa/graficos.py`, `qa/informe_lib.py`, `qa/generar_informe.py` | Figuras y PDF del informe |

## 6. Advertencias aprendidas

- Dos corridas de la suite al mismo tiempo falsean los resultados: usa una sola.
- Si cambias la contraseña de `admin` en la base de pruebas, fallan las pruebas con sesión.
- En Git Bash, anteponer `MSYS_NO_PATHCONV=1` a los comandos con rutas que empiezan con `/`.
- La suite deja datos de prueba (rutas y buses `QA`) en la base `buses_qa`; `qa_suite.py` los borra al empezar.
