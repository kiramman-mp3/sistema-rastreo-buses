# Análisis del problema y requisitos

Entregable 1 del proyecto final: «Documento de análisis y requisitos» (Actividad 1). Complementa la política de calidad (`docs/calidad/01-politica-y-alcance.md`) y se enlaza con la arquitectura
(`docs/arquitectura/ARQUITECTURA-Y-DATOS.md`) y la matriz de trazabilidad (`docs/calidad/19-matriz-de-trazabilidad.md`).

## 1. El problema

La Universidad Técnica de Ambato (UTA) mueve a sus estudiantes en buses por cuatro líneas (Huachi–Ingahurco, Huachi–Querochaca, Ingahurco–Izamba y Ambato–Píllaro). Hoy:

- el **pasajero** no sabe dónde está su bus ni si va a tiempo;
- la **administración** no puede comprobar si un bus salió a la hora, pasó por todas las paradas, siguió su ruta o llegó con retraso, y no tiene cifras para comparar líneas ni periodos;
- cuando algo falla (un bus sin señal, un desvío, un recorrido que no se hizo) no queda registro objetivo del hecho.

El proyecto no se limita a mostrar un bus en un mapa: **evalúa de manera objetiva el cumplimiento de las rutas y la calidad del propio sistema**, con indicadores que se calculan de los registros y se pueden comprobar.

## 2. Interesados

| Interesado | Qué necesita |
|---|---|
| Pasajero | Ver en vivo los buses de una línea sin crear cuenta; dejar una queja |
| Chofer | Iniciar y terminar su turno desde una tableta o celular; avisar un incidente o una emergencia; saber su horario |
| Despachador / supervisor | Ver todos los buses, las alertas abiertas, los recorridos del día y su retraso |
| Gestor del servicio | Definir líneas, paradas, horarios y asignaciones; leer los indicadores y compararlos; auditar el sistema |
| Administrador de sistemas | Desplegar, respaldar y vigilar el servidor; configurar Traccar, Grafana y los umbrales |
| Docente / evaluador | Comprobar cada indicador, cada regla y cada prueba (rúbrica del proyecto final) |

## 3. Requisitos funcionales

Cada uno tiene un criterio de aceptación comprobable y la prueba o evidencia que lo respalda. «R» indica la fase del plan (`docs/arquitectura/PLAN-RUBRICA.md`) donde se construyó lo nuevo.

| ID | Requisito | Criterio de aceptación | Prueba o evidencia |
|---|---|---|---|
| RF-01 | Registrar los vehículos de la flota en **Odoo Fleet** y enlazarlos con su bus rastreado (R8) | Crear un bus crea su vehículo de Fleet (marca UTA, modelo Bus) con placa, chofer y asientos; editar un lado actualiza el otro; los simulados no llegan a Fleet | `tests/test_fleet.py` (22); `docs/arquitectura/FLEET.md` |
| RF-02 | Administrar **rutas y paradas**, con los minutos planificados de cada parada (R1) | Una ruta necesita al menos 2 paradas; los minutos no retroceden a lo largo de la ruta; la distancia estimada sale del trazado | `tests/test_trips.py` |
| RF-03 | Definir **horarios** de cada línea y **asignar un bus por fecha y hora** (R1) | Un bus no puede tener dos recorridos a la misma hora; la asignación acepta de 1 a 92 días | `tests/test_trips.py`, `tests/test_boundaries.py` |
| RF-04 | Generar los **recorridos programados** de los próximos días (R1) | La tarea horaria crea los recorridos de los horarios con bus, sin duplicar | `tests/test_trips.py` |
| RF-05 | **Recibir y guardar posiciones** de Traccar (webhook y consulta periódica) (Act. 3) | Sin duplicados; se rechazan coordenadas imposibles, NaN, infinito y horas inválidas, y el rechazo queda registrado; sin turno no se guarda, salvo un bus con reporte de demostración | `tests/test_ingest.py`, `test_http.py`, `test_boundaries.py`, `test_demo_report.py` |
| RF-06 | **Mapa en vivo** de Odoo y **portal del pasajero** | Muestra solo buses reales con posición reciente; el pasajero no ve placa, chofer ni velocidad exacta | `tests/test_portal.py`, `qa/capturas_ui.py` |
| RF-07 | **Registrar cada recorrido**: hora programada y real, paradas visitadas con retraso, distancia estimada y recorrida, desvío (R2) | Al cerrarse el recorrido quedan sus paradas con estado (a tiempo, tarde, adelantado, omitida), duración, distancias y desviación | `tests/test_trip_run.py` |
| RF-08 | **Detectar incumplimientos** con reglas explícitas: llegada tarde, parada omitida, recorrido incompleto, salida tarde, duración distinta de la planificada, desvío, exceso de velocidad, sin señal, parada larga (R3) | Cada regla genera su alerta una sola vez por recorrido y parada; la tolerancia (5 min) y los límites son ajustes; en el límite exacto no hay alerta | `tests/test_trip_rules.py`, `docs/calidad/02-estandares-y-reglas.md` §1.1 |
| RF-09 | **Recorridos de prueba simulados**, identificados como tales (R4) | Doce recorridos con diez escenarios; cada uno declara qué debe detectarse y la comparación con lo detectado da 12 de 12; nunca aparecen en el mapa ni en el portal | `tests/test_trip_simulator.py`; `docs/calidad/13-recorridos-de-prueba.md` |
| RF-10 | **Ocho indicadores de transporte y cuatro de software**, cada uno con fórmula, fuente, unidad, resultado, estado e interpretación (R5) | Cada cifra sale de una consulta SQL mostrada junto a ella; ninguna es estática; cambiar los datos cambia la cifra | `tests/test_kpi.py`; `docs/calidad/14-metricas-de-transporte.md` |
| RF-11 | **Tablero dentro de Odoo** (R6) | Siete pestañas; filtros de periodo, línea y datos reales o simulados; comparación con el periodo anterior; se actualiza solo cada 30 s; estados con palabra y forma, no solo color | `tests/test_dashboard.py`; `docs/calidad/15-tablero-grafana.md` §2 |
| RF-12 | **Grafana incrustado en Odoo** como tablero complementario (R7) | Seis tableros; solo se entra con una sesión de Odoo; el rol de la base solo lee vistas `kpi_*`; las cifras son las del tablero de Odoo | `tests/test_grafana_*.py`; `qa/grafana_smoke.py` (19) |
| RF-13 | **Auditar la sincronización Traccar–Odoo** y **medir el rendimiento** (R5, R11) | La auditoría diaria compara posiciones; un reenvío perdido baja la exactitud y la consulta periódica la recupera; las consultas principales se miden y guardan | `tests/test_quality.py`, `test_traccar_consistency.py` |
| RF-14 | **Demostrar el sistema con Traccar Client** desde un celular por datos móviles (R9) | Un gestor activa «Start demo report» en un bus: solo ese bus acepta posiciones sin turno, por 8 horas | `tests/test_demo_report.py`; `docs/guias/DEMO-TRACCAR-CLIENT.md` |
| RF-15 | **Turnos y app del chofer**: iniciar y terminar turno, GPS, incidentes y SOS, avisos | Un chofer solo ve su turno; el GPS se apaga al terminar; el SOS exige mantener pulsado | `tests/test_driver_*.py`; 167 pruebas de Jest; `qa/tablet_*.py` |
| RF-16 | **Quejas de pasajeros** con protección contra abuso | Folio, límite por IP, contacto borrado a los 90 días de resuelta | `tests/test_complaints.py` |
| RF-17 | **Idiomas**: español por defecto, inglés y kichwa en web, tableta y oficina | Los 769 textos del módulo traducidos, sin entradas vacías | `qa/traducciones.py`, `TestLanguages`; `docs/guias/GLOSARIO-KICHWA.md` |

## 4. Requisitos no funcionales

| ID | Requisito | Criterio de aceptación | Medición |
|---|---|---|---|
| RNF-01 | **Rendimiento** | p95 menor que 2 000 ms en el mapa, el historial, la lista de recorridos, los indicadores y el tablero, hasta 100 000 posiciones y 5 000 recorridos | Todo bajo 160 ms; con 1 000 000 y 50 000, bajo 704 ms (`docs/calidad/17-rendimiento-por-volumen.md`) |
| RNF-02 | **Seguridad y privacidad** | Validación en el servidor; el identificador OsmAnd solo lo ve un gestor; el rol de Grafana solo lee vistas sin datos personales; acceso a Grafana solo con token de Odoo | `qa/auditoria.py`; `TestGrafanaRole`; `qa/grafana_smoke.py`; `docs/diseno/PRIVACIDAD.md` |
| RNF-03 | **Calidad del código** | Quality Gate de SonarQube aprobado; sin bugs ni vulnerabilidades abiertas sin justificar | 16 bugs → 0, 12 vulnerabilidades → 0 (`docs/calidad/16-sonarqube.md`) |
| RNF-04 | **Cobertura de pruebas** | Al menos 75 % de líneas del código | 78,4 % global; modelos 95 %, controladores 94 % |
| RNF-05 | **Verificabilidad de las métricas** | Ningún indicador estático ni ficticio; cada cifra se puede reproducir con su consulta | Pestaña «Formulas»; las pruebas comparan los dos tableros |
| RNF-06 | **Disponibilidad y vigilancia** | `/bus_tracking/health` responde 200 con datos frescos; copias de seguridad programables | `tests/test_http.py`; `scripts/backup.sh` |
| RNF-07 | **Accesibilidad y usabilidad** | Contraste AAA, estados con palabra y forma, probado con la fuente del sistema al 130 % y al 200 % | `qa/contraste.py`, `qa/accesibilidad.py`, `docs/calidad/12-validacion-ux.md` |
| RNF-08 | **Despliegue reproducible** | Un comando levanta el stack; las migraciones se prueban sobre una copia | `docker-compose*.yml`, `scripts/init-prod.sh`, `migrations/` |
| RNF-09 | **Trazabilidad del trabajo** | Flujo Git con ramas por tarea, commits pequeños, integración con `--no-ff` y pruebas en verde | Historial de Git; `docs/academico/BITACORA.md` |
| RNF-10 | **Mantenibilidad** | Los tableros de Grafana y los documentos de métricas y calidad se generan desde el código | `scripts/gen_grafana_dashboards.py`, `scripts/doc_metricas.py`, `qa/generar_docs.py` |

## 5. Supuestos y restricciones

- Los **horarios** de las cuatro líneas son simulados hasta que la UTA confirme los oficiales; los recorridos simulados se identifican como tales (`simulated`) y nunca se mezclan en silencio con los reales.
- La **tolerancia** de 5 minutos, la ventana de 30 minutos y el retraso de salida de 10 minutos son ajustes del gestor (Ajustes › Trips and punctuality); cambiarlos cambia las cifras.
- La **demostración física** con Traccar Client requiere un celular real el día de la defensa (`docs/guias/DEMO-TRACCAR-CLIENT.md`).
- La edición Community de SonarQube no analiza inyecciones ni dependencias (`docs/calidad/16-sonarqube.md` §4.4).
- El kichwa fue traducido por una IA sin revisión de una persona hablante.
