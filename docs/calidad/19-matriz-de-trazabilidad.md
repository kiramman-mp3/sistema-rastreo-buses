# Matriz de trazabilidad del proyecto final

Cada actividad, entregable y criterio de la rúbrica (`proyectoFinal_GC.pdf`) con el archivo que lo demuestra y su estado. «Hecho» quiere decir que la evidencia está en el repositorio y se puede abrir; lo que depende de algo
que no está en el repositorio (el celular real, la confirmación del docente) se marca como **pendiente** y se explica.

## 1. Actividades

| # | Actividad del PDF | Qué se hizo | Evidencia | Estado |
|---|---|---|---|---|
| 1 | Análisis del problema y requisitos | Problema, interesados, 17 requisitos funcionales y 10 no funcionales con criterio de aceptación | `docs/arquitectura/REQUISITOS.md`, `docs/calidad/01-politica-y-alcance.md` | Hecho |
| 2 | Infraestructura (Odoo 16, **Fleet**, Traccar, conectividad externa, **Traccar Client**) | Odoo y Traccar en Docker; Azure con Caddy y HTTPS (alternativa equivalente a Cloudflare Tunnel); Fleet instalado y enlazado a cada bus; guía y reporte de demostración para Traccar Client | `docker-compose*.yml`, `proxy/Caddyfile`, `docs/guias/PRODUCCION.md`, `docs/arquitectura/FLEET.md`, `docs/guias/DEMO-TRACCAR-CLIENT.md` | Hecho; **capturas con el celular pendientes** (lista de evidencias §5 de la guía) |
| 3 | Integración Odoo–Traccar | Webhook y consulta periódica, sin duplicados, validación, auditoría de sincronización | `models/bus_vehicle.py`, `tests/test_ingest.py`, `test_http.py`, `test_traccar_consistency.py` | Hecho |
| 4 | Vehículos, rutas y paradas; horarios y asignación | 6 buses, 4 rutas con 4 a 6 paradas, minutos planificados, horarios y asignación por fecha y hora | `models/bus_route.py`, `bus_trip.py`, `tests/test_trips.py`, `test_boundaries.py` | Hecho (horarios simulados hasta confirmar los oficiales) |
| 5 | Monitoreo y registro de recorridos (10 recorridos de prueba) | Recorrido con hora programada y real, distancias estimada y recorrida, paradas con retraso; **12 recorridos simulados** identificados | `docs/calidad/13-recorridos-de-prueba.md`, `tests/test_trip_run.py`, `test_trip_simulator.py`, `scripts/seed_recorridos.py` | Hecho |
| 6 | Incumplimientos e incidencias | Reglas de llegada tarde, parada omitida, recorrido incompleto, salida tarde, duración, desvío, velocidad, sin señal, parada larga | `docs/calidad/02-estandares-y-reglas.md` §1.1, `tests/test_trip_rules.py` | Hecho |
| 7 | Métricas e indicadores (8 de transporte, 4 de software) | Doce indicadores con fórmula, fuente, unidad, consulta, umbrales, estado e interpretación | `docs/calidad/14-metricas-de-transporte.md` (generado del código), `tests/test_kpi.py` | Hecho |
| 8 | Dashboard y reportes | Tablero dentro de Odoo (7 pestañas) y Grafana incrustado (6 tableros); reportes de alertas con pivote y gráfico | `docs/calidad/15-tablero-grafana.md`, `tests/test_dashboard.py`, `test_grafana_*.py`, `qa/grafana_smoke.py` | Hecho; **confirmar con el docente que Grafana sirve en lugar de Power BI** (el tablero de Odoo es la alternativa A completa) |
| 9 | Pruebas y calidad (matriz, ISO/IEC 25010, SonarQube, rendimiento) | 544 pruebas de Odoo, 167 de Jest, suite en vivo, auditoría; SonarQube con Quality Gate; rendimiento por volumen | `docs/calidad/03`, `04`, `09`, `16-sonarqube.md`, `17-rendimiento-por-volumen.md` | Hecho |
| 10 | Problemas y mejora continua | 48 defectos con causa raíz; Ishikawa, Pareto y cuatro ciclos PDCA con antes y después | `05`, `07`, `08`, `18-mejora-continua-pdca.md` | Hecho |

## 2. Entregables finales

| # | Entregable | Archivo o lugar | Estado |
|---|---|---|---|
| 1 | Documento de análisis y requisitos | `docs/arquitectura/REQUISITOS.md` | Hecho |
| 2 | Arquitectura y modelo de datos | `docs/arquitectura/ARQUITECTURA-Y-DATOS.md`, `PLAN.md` | Hecho |
| 3 | Sistema Odoo 16 integrado con Traccar | `addons/bus_tracking/`, `docker-compose*.yml` | Hecho |
| 4 | Conectividad externa funcional | Servidor en Azure con HTTPS (`docs/guias/PRODUCCION.md`) y `gps.<dominio>`; prueba con datos móviles | Hecho en el servidor; **prueba con celular pendiente** |
| 5 | Módulo desarrollado o adaptado para administrar rutas | `bus_tracking`: rutas, paradas, horarios, asignación, recorridos y Fleet | Hecho |
| 6 | Historial de recorridos y datos GPS | `bus.trip`, `bus.trip.stop`, `bus.position`; menús Scheduled trips y Reports | Hecho |
| 7 | Indicadores calculados y dashboard dentro de Odoo | Buses › Indicators › Odoo dashboard; `14-metricas-de-transporte.md` | Hecho |
| 8 | Matriz y evidencias de pruebas | `docs/calidad/03-plan-y-casos-de-prueba.md`, `evidencias/`, esta matriz | Hecho |
| 9 | Análisis de calidad mediante SonarQube | `docs/calidad/16-sonarqube.md`, `evidencias/sonarqube/` | Hecho |
| 10 | Informe de mejora continua y código fuente | `docs/calidad/18-mejora-continua-pdca.md`, `Informe_calidad_rastreo_buses.pdf`, el repositorio | Hecho |

## 3. Criterios de la rúbrica

| # | Criterio | Dónde se demuestra |
|---|---|---|
| 1 | Análisis y requisitos | `REQUISITOS.md` |
| 2 | Arquitectura e infraestructura | `ARQUITECTURA-Y-DATOS.md`, `FLEET.md`, `PRODUCCION.md`, `DEMO-TRACCAR-CLIENT.md` §6 |
| 3 | Integración Odoo–Traccar y monitoreo GPS | `test_traccar_consistency.py`, auditoría S2, guía de demostración |
| 4 | Rutas, paradas y recorridos: horarios y asignaciones | `bus_trip.py`, formularios de horarios y asistente de asignación |
| 5 | Historial e incidencias | `13-recorridos-de-prueba.md`, reglas §1.1, reportes de alertas |
| 6 | Métricas y tablero | `14-metricas-de-transporte.md`, `15-tablero-grafana.md` |
| 7 | Pruebas funcionales, de integración y de rendimiento | `03`, `17-rendimiento-por-volumen.md`, `tests/` |
| 8 | Calidad del software: ISO 25010 y SonarQube | `09-cumplimiento-iso.md`, `16-sonarqube.md` |
| 9 | Mejora continua | `18-mejora-continua-pdca.md`, `05`, `07`, `08` |
| 10 | Presentación y defensa | `docs/academico/GUION_DEFENSA.md` parte A |

## 4. Las preguntas que el sistema debe responder

Cada pregunta del PDF (§6) con su pantalla está en `docs/academico/GUION_DEFENSA.md`, sección A.4.

## 5. Restricciones del PDF y cómo se cumplen

| Restricción | Cómo |
|---|---|
| No basta instalar Odoo, Traccar y Cloudflare ni ver un vehículo en un mapa | Hay recorridos, reglas, indicadores, tableros, pruebas y análisis de calidad |
| Administrar múltiples rutas, registrar historial, evaluar cumplimiento, métricas verificables | Cuatro rutas, `bus.trip` e historial, reglas §1.1, consulta SQL junto a cada indicador |
| Aplicar pruebas, identificar defectos y demostrar mejoras | 544 + 167 pruebas, 48 defectos, PDCA con antes y después |
| **No dashboards estáticos, ni datos ficticios como reales, ni métricas incomprobables** | Cada cifra es una consulta; los simulados llevan `simulated` y se filtran; las pruebas comparan los dos tableros con las fórmulas |

## 6. Lo que queda pendiente

| Pendiente | Quién | Por qué no está hecho |
|---|---|---|
| Capturas con el celular real (Traccar Client, datos móviles) | Equipo | Requiere un celular y el servidor público el día de la prueba |
| Ensayo de la defensa con el celular | Equipo | Idem |
| Confirmar con el docente que Grafana reemplaza a Power BI | Equipo | Decisión del docente; el tablero de Odoo cubre el criterio por sí solo |
| Revisión del kichwa por una persona hablante | Comunidad | La traducción la hizo una IA |
| Pruebas unitarias del JavaScript del módulo; `npm audit`; prueba de concurrencia | Equipo | Siguiente ciclo (`18-mejora-continua-pdca.md` §5) |
| **Desplegar la versión 16.0.1.6.0 en Azure** (respaldo, migración de Fleet y de las vistas, Grafana con su subdominio) | Equipo | El servidor sigue en la versión anterior; el despliegue modifica la base de producción y se hace con respaldo (`docs/guias/GRAFANA.md` §3, `docs/arquitectura/FLEET.md` §4) |
| Subir los cambios a GitHub (`develop` y `main`) | Equipo | Se hace cuando lo decida el equipo |
