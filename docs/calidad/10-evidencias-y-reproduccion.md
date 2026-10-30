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

Un solo comando, desde `cmd`, PowerShell o Git Bash, con Docker Desktop abierto. Crea lo que falte (Postgres, la base `buses_qa` con el módulo, el servidor `qa-odoo`), reinicia `qa-odoo` antes de medir, ejecuta las pruebas de Odoo con cobertura en una base desechable (`buses_unit`) y luego la suite en vivo, la auditoría y las métricas:

```bash
cp .env.example .env                       # una sola vez; sin .env se usan los valores por defecto
python -X utf8 qa/ejecutar_todo.py         # todo (también: sh qa/ejecutar_todo.sh)
python -X utf8 qa/ejecutar_todo.py suite   # un solo paso: odoo, suite, auditoria o metricas
python -X utf8 qa/generar_docs.py          # documentos 03, 04, 05, 07 y las figuras
python -X utf8 qa/generar_informe.py       # informe en PDF
python -X utf8 qa/ejecutar_todo.py --limpiar   # elimina qa-odoo y las bases de pruebas
```

La primera vez tarda unos minutos (crea la base e instala `coverage`). `suite` y `auditoria` reinician `qa-odoo` solos. El paso `metricas` lee los resultados de `odoo`, así que en una carpeta de evidencias vacía hay que ejecutar `odoo` antes. Para no pisar las evidencias guardadas, apunta la salida a otra carpeta con `QA_OUT`.

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
