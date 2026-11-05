# Rendimiento por volumen

Evidencia de las actividades 9 y 10 del proyecto final (criterio 7, pruebas funcionales, de integración y de rendimiento) y del indicador de software S3 (tiempo de respuesta, meta: p95 menor que 2 s).
Pregunta que responde: **¿qué pasa con las pantallas cuando los datos crecen?**

## 1. Cómo se mide

`qa/rendimiento_volumen.py` arma una base de datos desechable (`buses_perf`) con las líneas y los buses de desarrollo, levanta un **Odoo real** en un contenedor, llena las tablas con el volumen de cada
escenario (`qa/rendimiento_volumen.sql`) y mide **por HTTP, como administrador**, lo que pide cada pantalla. Cada llamada se repite 15 veces después de una de calentamiento y se informa la
mediana (p50), el percentil 95 (p95), el máximo y el tamaño de la respuesta.

```bash
python -X utf8 qa/rendimiento_volumen.py                                        # los tres escenarios -> evidencias/rendimiento.json
python -X utf8 qa/rendimiento_volumen.py --scenarios 1000000:50000 --out docs/calidad/evidencias/rendimiento-estres.json
```

| Pantalla o consulta | Qué se llama |
|---|---|
| Mapa en vivo, refresco | `/bus_tracking/live` con la clave de las líneas (lo que se pide cada pocos segundos) |
| Mapa en vivo, primera carga | `/bus_tracking/live` sin clave: manda también las líneas y las paradas |
| Historial de un bus | `bus.position.search_read` de las últimas 4 horas del bus, hasta 5 000 puntos |
| Lista de recorridos | `bus.trip.search_read` (80 filas) y `search_count` |
| Indicadores | `bus.kpi.compute()` de los últimos 30 días (los 12 indicadores) |
| Tablero | `/bus_tracking/dashboard` de 30 y de 90 días (indicadores, series y tablas) |

Los datos son sintéticos pero con la forma real: una posición cada 5 segundos por bus (lo que envía Traccar Client), recorridos repartidos en 60 días (1 de cada 5 incompleto, 1 de cada 20 simulado),
5 paradas por recorrido (85 % a tiempo, 10 % tarde, 5 % omitidas) y una alerta por cada tres recorridos.

## 2. Resultados

Máquina de desarrollo (Docker Desktop, 20 CPU, base de datos local, Odoo con `--workers=0`). Tiempos en milisegundos.

| Escenario | Posiciones | Recorridos | Paradas de recorrido | Alertas |
|---|---|---|---|---|
| Pequeño | 1 000 | 100 | 500 | 33 |
| Mediano | 10 000 | 1 000 | 5 000 | 333 |
| Grande | 100 000 | 5 000 | 25 001 | 1 666 |
| **Estrés (10 veces el grande)** | 1 000 000 | 50 000 | 250 001 | 16 666 |

| Pantalla (p50 / **p95**) | Pequeño | Mediano | Grande | Estrés |
|---|---|---|---|---|
| Mapa en vivo, refresco | 22 / **48** | 38 / **44** | 28 / **39** | 37 / **51** |
| Mapa en vivo, primera carga | 22 / **40** | 26 / **38** | 32 / **48** | 29 / **39** |
| Historial de un bus (4 h) | 23 / **35** | 49 / **84** | 74 / **89** | 77 / **93** |
| Lista de recorridos | 51 / **61** | 54 / **63** | 46 / **60** | 40 / **51** |
| Indicadores (30 días) | 17 / **36** | 40 / **53** | 74 / **99** | 211 / **218** |
| Tablero (30 días) | 33 / **51** | 66 / **79** | 136 / **151** | 616 / **687** |
| Tablero (90 días) | 50 / **59** | 62 / **79** | 131 / **156** | 686 / **704** |

El detalle de cada escenario (con el máximo y el tamaño de cada respuesta) está en `evidencias/rendimiento.json` y `evidencias/rendimiento-estres.json`.

**Resultado: ninguna pantalla superó la meta de 2 000 ms (p95) en ningún escenario.** El peor caso es el tablero con 50 000 recorridos, 704 ms, tres veces por debajo de la meta.

## 3. Lectura

- **Lo que crece con las posiciones casi no se nota.** El mapa en vivo no depende del volumen: lee el último punto que cada bus guarda en su propio registro (`last_*`), no el historial. El historial de un bus sube de
  35 a 93 ms con mil veces más posiciones, porque el índice único `(vehicle_id, fix_time)` de `bus_position` lo resuelve sin recorrer la tabla.
- **Lo que crece con los recorridos es lo que cuesta.** Los indicadores y el tablero suman sobre los recorridos y las paradas del periodo, y crecen en proporción (36 → 99 → 218 ms los indicadores). Aun con diez veces el escenario grande, el tablero tarda 0,7 s.
- **Los volúmenes son realistas o mayores.** Con la retención de 30 días (`bus_tracking.retention_days`) y un bus que reporta cada 5 s durante unas 10 horas al día, 6 buses guardan cerca de 1,3 millones de posiciones:
  el escenario de estrés es el volumen normal de las posiciones. En recorridos, 6 buses con 25 recorridos diarios cada uno hacen unos 150 al día, 9 000 en 60 días: entre el escenario grande (5 000) y el de estrés (50 000, cinco veces más).
- **No hizo falta añadir índices.** Los que ya existen cubren las consultas: `(vehicle_id, fix_time)` único en las posiciones; `date`, `planned_start`, `state`, `route_id` y `vehicle_id` en los recorridos; `trip_id`, `status` y `date`
  en las paradas; `vehicle_id` y `kind` en las alertas. Como ninguna pantalla se acerca a la meta, no se agregó ninguno: un índice de más hace más lentas las escrituras (cada posición que llega).
- **El tamaño de las respuestas no preocupa**: la mayor (historial de un bus con 2 868 puntos) pesa 355 KB; el tablero, 32 KB.

## 4. Límites de esta medición

- Se midió **en la máquina de desarrollo**, no en la VM pequeña de Azure; allí los tiempos serán mayores. La proporción entre escenarios sí se mantiene: con la meta a 2 000 ms y el peor caso a 704 ms hay margen
  de casi 3 veces. El indicador S3 mide los tiempos reales del servidor (`bus.perf.sample`, botón «Medir ahora» del tablero) y es el que debe vigilarse en producción.
- Es **un solo usuario a la vez**. No se midió la concurrencia (varios gestores con el mapa abierto y 20 tabletas enviando a la vez); para el tamaño del proyecto (6 buses) no se espera que importe, y Odoo en producción
  corre con varios procesos.
- Son 6 buses y 4 líneas. El mapa en vivo crece con la cantidad de buses, no con las posiciones; con 100 buses seguiría sumando solo 100 filas de `bus_vehicle`.

## 5. Pruebas de funciones y de integración que acompañan a la medición

| Qué | Dónde |
|---|---|
| **Caja negra** de las reglas nuevas: valores válidos, inválidos y en el límite (asistente de asignación de 92 y 93 días, coordenadas en las esquinas del planeta y un paso más allá, NaN e infinito, tolerancia de puntualidad exacta, periodo de los indicadores) | `tests/test_boundaries.py` (26), `tests/test_trip_run.py`, `tests/test_trip_rules.py` |
| **Caja blanca** del cálculo de retraso, parada omitida e indicadores, con casos hechos a mano y resultado conocido | `tests/test_trip_run.py`, `tests/test_kpi.py` (cada fórmula contra datos construidos) |
| **Integración Traccar–Odoo con la auditoría de sincronización (S2)**: el webhook guarda lo que Traccar reenvía; un reenvío perdido aparece como «falta» y baja la exactitud a 80 %; un reenvío repetido no duplica; un secreto malo no guarda nada; la consulta periódica recupera la última posición perdida y la exactitud vuelve a 100 % | `tests/test_traccar_consistency.py` (6), `tests/test_quality.py` |
| Cobertura de líneas de los módulos nuevos | `bus_trip.py` 98 %, `bus_kpi.py` 99 %, `trip_simulator.py` 99 %, `bus_fleet.py` 99 %, `bus_grafana.py` y `bus_kpi_views.py` 100 % (informe de `scripts/sonar-coverage.sh`) |
