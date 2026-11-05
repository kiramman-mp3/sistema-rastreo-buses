# Métricas de transporte y de software

Evidencia de la Actividad 7 del proyecto final (criterio 6, métricas y tablero): **8 métricas de transporte y 4 de calidad del software**, cada una con su fórmula, su fuente de datos, su unidad,
su resultado, su estado y su interpretación. Este documento **se genera desde el código** (`scripts/doc_metricas.py` lee `models/bus_kpi.py` y calcula cada cifra al momento): no hay ningún valor escrito a mano.

Las mismas cifras se ven en el menú **Buses › Indicators › Odoo dashboard** (pestaña «Formulas», con la consulta de cada una) y en **Grafana** (`docs/calidad/15-tablero-grafana.md`);
las pruebas comprueban que los dos tableros dan las mismas cifras que estas consultas (`TestSameFiguresAsTheIndicators`).

## 1. Cómo se calculan

- **Nada es estático.** Cada indicador es una consulta SQL sobre los registros guardados. Al entrar un recorrido, una llegada, una alerta o una posición, la cifra cambia en la siguiente consulta.
- **Periodo.** Por defecto, los últimos 30 días (fecha local de Ecuador). El tablero permite 7, 30 o 90 días o fechas elegidas, una o varias líneas, y datos reales, simulados o ambos.
- **Recorridos que cuentan.** Solo los recorridos **cerrados** (hechos o incompletos). Un recorrido que aún corre no entra hasta que termina.
- **Datos simulados.** Los recorridos simulados llevan `simulated = True` y su escenario; nunca se mezclan en silencio con los reales (filtro «Real / Simulated / Both»).
- **Tolerancias** (Ajustes › Trips and punctuality): puntualidad 5 min; ventana del recorrido 30 min; salida tarde 10 min; duración marcada a partir de 25 %. Cambiarlas cambia las cifras.
- **Parámetros de las consultas:** `%(d1)s` y `%(d2)s` son el primer y el último día del periodo; `%(routes)s` es la lista de líneas (vacía = todas); `%(scope)s` es `all`, `real` o `simulated`.

## 2. Resumen de la corrida

Corrida del 2026-11-05 en la base de **desarrollo**, con datos **simulados** (12 recorridos cerrados, identificados como simulados; ver `docs/calidad/13-recorridos-de-prueba.md`), periodo 2026-10-06 a 2026-11-04.

| Código | Indicador | Unidad | Resultado | Estado | Umbrales |
|---|---|---|---|---|---|
| T1 | Cumplimiento de la ruta | % | **75** | atención | Verde desde 90 %, ámbar desde 75 %, rojo por debajo. |
| T2 | Puntualidad | % | **86,3** | en la meta | Verde desde 85 %, ámbar desde 70 %, rojo por debajo. |
| T3 | Retraso promedio | min | **10,5** | fuera de la meta | Verde hasta 5 min, ámbar hasta 10 min, rojo por encima. |
| T4 | Paradas atendidas | % | **89,5** | atención | Verde desde 95 %, ámbar desde 85 %, rojo por debajo. |
| T5 | Desviación de la ruta | m | **32,8** | en la meta | Verde hasta 50 m, ámbar hasta 150 m, rojo por encima. |
| T6 | Distancia estimada contra recorrida | % | **-0,7** | en la meta | Verde hasta 5 %, ámbar hasta 10 %, rojo por encima (se juzga sobre el valor absoluto de la diferencia). |
| T7 | Tiempo promedio de recorrido | min | **27,2** | en la meta | Verde hasta 15 min, ámbar hasta 30 min, rojo por encima (se juzga sobre el valor absoluto de la diferencia). |
| T8 | Incidentes | n | **16** | cifra sin umbral | Sin umbral: es un conteo; se compara entre líneas y entre periodos. |
| S1 | Integridad de los registros GPS | % | **100** | en la meta | Verde desde 99 %, ámbar desde 95 %, rojo por debajo. |
| S2 | Exactitud de la sincronización de Traccar a Odoo | % | **—** | sin datos | Verde desde 99 %, ámbar desde 95 %, rojo por debajo. |
| S3 | Tiempo de respuesta | ms | **92,3** | en la meta | Verde hasta 500 ms, ámbar hasta 2000 ms, rojo por encima. |
| S4 | Detección correcta de incidencias | % | **100** | en la meta | Verde desde 90 %, ámbar desde 75 %, rojo por debajo. |

Los indicadores S1 y S2 miden el sistema con Traccar real: en desarrollo no hay auditoría de sincronización (S2 «sin datos») ni posiciones rechazadas. En producción se calculan con los registros reales.

## 3. Cada indicador

### Servicio de transporte

#### T1 · Cumplimiento de la ruta

| | |
|---|---|
| **Qué mide** | Porcentaje de los recorridos que hicieron toda la ruta. Debajo de 75 % el servicio les falla a los pasajeros. |
| **Fórmula** | recorridos cerrados que llegaron a todas las paradas ÷ recorridos cerrados × 100 |
| **Fuente de datos** | `bus.trip (estado hecho o incompleto)` |
| **Unidad** | % |
| **Umbrales** | Verde desde 90 %, ámbar desde 75 %, rojo por debajo. |
| **Resultado de esta corrida** | **75 %**, atención: 9 de 12 recorridos cerrados |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT COUNT(*) FILTER (WHERE state = 'done'), COUNT(*) FROM f
```

#### T2 · Puntualidad

| | |
|---|---|
| **Qué mide** | Porcentaje de llegadas a tiempo o adelantadas. Una llegada adelantada no es un retraso. |
| **Fórmula** | llegadas no más tarde que la tolerancia ÷ llegadas registradas × 100 |
| **Fuente de datos** | `bus.trip.stop (estado, con la tolerancia de Ajustes)` |
| **Unidad** | % |
| **Umbrales** | Verde desde 85 %, ámbar desde 70 %, rojo por debajo. |
| **Resultado de esta corrida** | **86,3 %**, en la meta: 44 de 51 llegadas |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT COUNT(*) FILTER (WHERE s.status <> 'late'), COUNT(*)
                      FROM bus_trip_stop s JOIN f ON f.id = s.trip_id WHERE s.actual_time IS NOT NULL
```

#### T3 · Retraso promedio

| | |
|---|---|
| **Qué mide** | Qué tan tarde llega un bus tarde. Hasta 5 min es tolerable; más de 10 min los pasajeros lo notan. |
| **Fórmula** | promedio del retraso de las llegadas tarde |
| **Fuente de datos** | `bus.trip.stop (estado tarde, delay_min)` |
| **Unidad** | min |
| **Umbrales** | Verde hasta 5 min, ámbar hasta 10 min, rojo por encima. |
| **Resultado de esta corrida** | **10,5 min**, fuera de la meta: 7 llegadas tarde, la peor de 13.6 min |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT AVG(s.delay_min), MAX(s.delay_min), COUNT(*)
                      FROM bus_trip_stop s JOIN f ON f.id = s.trip_id WHERE s.status = 'late'
```

#### T4 · Paradas atendidas

| | |
|---|---|
| **Qué mide** | Porcentaje de las paradas planificadas a las que los buses de verdad llegaron. |
| **Fórmula** | paradas con una llegada ÷ paradas planificadas en los recorridos cerrados × 100 |
| **Fuente de datos** | `bus.trip.stop` |
| **Unidad** | % |
| **Umbrales** | Verde desde 95 %, ámbar desde 85 %, rojo por debajo. |
| **Resultado de esta corrida** | **89,5 %**, atención: 51 de 57 paradas planificadas |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT COUNT(*) FILTER (WHERE s.actual_time IS NOT NULL), COUNT(*)
                      FROM bus_trip_stop s JOIN f ON f.id = s.trip_id
```

#### T5 · Desviación de la ruta

| | |
|---|---|
| **Qué mide** | Qué tan lejos de la ruta andan los buses. Menos de 50 m la siguen; más de 150 m la dejan. |
| **Fórmula** | distancia promedio de las posiciones de cada recorrido a la línea de la ruta, promediada entre recorridos |
| **Fuente de datos** | `bus.trip (deviation_avg_m, deviation_max_m, corridor_pct)` |
| **Unidad** | m |
| **Umbrales** | Verde hasta 50 m, ámbar hasta 150 m, rojo por encima. |
| **Resultado de esta corrida** | **32,8 m**, en la meta: peor posición 500.9 m; 93.4 % de las posiciones dentro del corredor |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT AVG(COALESCE(deviation_avg_m, 0)), MAX(COALESCE(deviation_max_m, 0)),
                           AVG(COALESCE(corridor_pct, 0)), COUNT(*)
                      FROM f WHERE distance_real_km > 0
```

#### T6 · Distancia estimada contra recorrida

| | |
|---|---|
| **Qué mide** | Positivo: los buses recorren más que la ruta (desvíos). Dentro del 5 % la estimación es confiable. |
| **Fórmula** | (km recorridos − km estimados) ÷ km estimados × 100 |
| **Fuente de datos** | `bus.trip (distance_est_km, distance_real_km)` |
| **Unidad** | % |
| **Umbrales** | Verde hasta 5 %, ámbar hasta 10 %, rojo por encima (se juzga sobre el valor absoluto de la diferencia). |
| **Resultado de esta corrida** | **-0,7 %**, en la meta: 97.2 km recorridos contra 97.9 km estimados |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT SUM(distance_est_km), SUM(distance_real_km), COUNT(*)
                      FROM f WHERE distance_real_km > 0
```

#### T7 · Tiempo promedio de recorrido

| | |
|---|---|
| **Qué mide** | Compáralo con el tiempo planificado: dentro del 15 % del plan el horario es realista. |
| **Fórmula** | duración real promedio de los recorridos que llegaron a la última parada; se juzga contra la planificada |
| **Fuente de datos** | `bus.trip (duration_real_min, duration_est_min)` |
| **Unidad** | min |
| **Umbrales** | Verde hasta 15 min, ámbar hasta 30 min, rojo por encima (se juzga sobre el valor absoluto de la diferencia). |
| **Resultado de esta corrida** | **27,2 min**, en la meta: planificado 24.2 min (12.5 % frente al plan) |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT AVG(duration_real_min), AVG(duration_est_min), COUNT(*)
                      FROM f WHERE state = 'done' AND duration_real_min > 0
```

#### T8 · Incidentes

| | |
|---|---|
| **Qué mide** | Con qué frecuencia algo sale mal, por tipo. Compara la tasa por cada 100 km entre las rutas. |
| **Fórmula** | cantidad de alertas e incidentes de los choferes, y por cada 100 km recorridos |
| **Fuente de datos** | `bus.alert, bus.incident, bus.trip (distance_real_km)` |
| **Unidad** | n |
| **Umbrales** | Sin umbral: es un conteo; se compara entre líneas y entre periodos. |
| **Resultado de esta corrida** | **16 n**, cifra sin umbral: 16 alertas e 0 incidentes; 16.5 por cada 100 km. Llegada tarde 7, Recorrido incompleto 3, Fuera de ruta 2, Parada omitida 2 |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT 'alert', a.kind, COUNT(*)
                      FROM bus_alert a JOIN bus_vehicle v ON v.id = a.vehicle_id
                     WHERE (a.start_time - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s
                       AND (%(routes)s::int[] IS NULL OR a.route_id = ANY(%(routes)s::int[]))
                       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT v.simulated)
                            OR (%(scope)s = 'simulated' AND v.simulated))
                     GROUP BY a.kind
                    UNION ALL
                    SELECT 'incident', i.kind, COUNT(*)
                      FROM bus_incident i JOIN bus_vehicle v ON v.id = i.vehicle_id
                     WHERE (i.reported_at - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s
                       AND (%(routes)s::int[] IS NULL OR i.route_id = ANY(%(routes)s::int[]))
                       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT v.simulated)
                            OR (%(scope)s = 'simulated' AND v.simulated))
                     GROUP BY i.kind

WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT COALESCE(SUM(distance_real_km), 0) FROM f
```

### Calidad del software

#### S1 · Integridad de los registros GPS

| | |
|---|---|
| **Qué mide** | Porcentaje de las posiciones recibidas que eran válidas. Las rechazadas tenían datos imposibles. |
| **Fórmula** | posiciones guardadas ÷ (posiciones guardadas + posiciones rechazadas) × 100 |
| **Fuente de datos** | `bus.position, bus.position.reject` |
| **Unidad** | % |
| **Umbrales** | Verde desde 99 %, ámbar desde 95 %, rojo por debajo. |
| **Resultado de esta corrida** | **100 %**, en la meta: 306 guardadas, 0 rechazadas |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
SELECT COUNT(*) FROM bus_position p JOIN bus_vehicle v ON v.id = p.vehicle_id
               WHERE (p.fix_time - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s
                 AND (%(routes)s::int[] IS NULL OR v.route_id = ANY(%(routes)s::int[]))
                 AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT v.simulated)
                      OR (%(scope)s = 'simulated' AND v.simulated))

SELECT COUNT(*) FROM bus_position_reject r
               WHERE (r.create_date - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s
```

#### S2 · Exactitud de la sincronización de Traccar a Odoo

| | |
|---|---|
| **Qué mide** | Si Odoo conserva lo que Traccar recibió. Debajo de 95 % se están perdiendo posiciones. |
| **Fórmula** | posiciones iguales en Traccar y Odoo ÷ posiciones que Traccar guarda de buses con turno × 100 |
| **Fuente de datos** | `bus.sync.audit (compara /api/positions de Traccar con bus.position)` |
| **Unidad** | % |
| **Umbrales** | Verde desde 99 %, ámbar desde 95 %, rojo por debajo. |
| **Resultado de esta corrida** | **— **, sin datos: 0 de 0 posiciones en 0 auditorías |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
SELECT COALESCE(SUM(matched), 0), COALESCE(SUM(total), 0), COUNT(*) FROM bus_sync_audit
              WHERE (run_at - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s
```

#### S3 · Tiempo de respuesta

| | |
|---|---|
| **Qué mide** | La meta del proyecto es un p95 menor que 2 000 ms; la mediana debe quedar muy por debajo. |
| **Fórmula** | Percentil 95 del tiempo de las consultas del mapa, el historial, los recorridos y los indicadores |
| **Fuente de datos** | `bus.perf.sample` |
| **Unidad** | ms |
| **Umbrales** | Verde hasta 500 ms, ámbar hasta 2000 ms, rojo por encima. |
| **Resultado de esta corrida** | **92,3 ms**, en la meta: mediana de 1.1 ms en 8 muestras |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY ms), percentile_cont(0.95) WITHIN GROUP (ORDER BY ms),
                    COUNT(*) FROM bus_perf_sample
              WHERE (created - interval '5 hours')::date BETWEEN %(d1)s AND %(d2)s
```

#### S4 · Detección correcta de incidencias

| | |
|---|---|
| **Qué mide** | Qué tan bien encuentran las reglas lo que se sembró. La precisión y la exhaustividad están en el detalle. |
| **Fórmula** | recorridos simulados cuyos incidentes detectados son iguales a los esperados ÷ recorridos simulados × 100 |
| **Fuente de datos** | `bus.trip (expected_flags, detected_flags de los recorridos simulados)` |
| **Unidad** | % |
| **Umbrales** | Verde desde 90 %, ámbar desde 75 %, rojo por debajo. |
| **Resultado de esta corrida** | **100 %**, en la meta: precisión 100.0 %, exhaustividad 100.0 % en 12 recorridos simulados |

Consulta que la reproduce (la misma que ejecuta el tablero):

```sql
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN %(d1)s AND %(d2)s
       AND t.state IN ('done', 'incomplete')
       AND (%(routes)s::int[] IS NULL OR t.route_id = ANY(%(routes)s::int[]))
       AND (%(scope)s = 'all' OR (%(scope)s = 'real' AND NOT t.simulated) OR (%(scope)s = 'simulated' AND t.simulated))
)
SELECT id FROM f WHERE simulated AND expected_flags IS NOT NULL
```

## 4. Cómo comprobar una cifra por su cuenta

1. En Odoo, **Buses › Indicators › Odoo dashboard › Formulas** muestra, para cada indicador, la fórmula, la fuente y la consulta.
2. En la base: ejecutar la consulta con los parámetros del periodo, por ejemplo en `psql`:

```sql
-- T1 del periodo de esta corrida, todas las líneas, datos reales y simulados: devuelve (recorridos hechos, recorridos cerrados)
WITH f AS (
    SELECT t.* FROM bus_trip t
     WHERE t.date BETWEEN '2026-10-06' AND '2026-11-04'
       AND t.state IN ('done', 'incomplete')
       AND (NULL::int[] IS NULL OR t.route_id = ANY(NULL::int[]))
       AND ('all' = 'all' OR ('all' = 'real' AND NOT t.simulated) OR ('all' = 'simulated' AND t.simulated))
)
SELECT COUNT(*) FILTER (WHERE state = 'done'), COUNT(*) FROM f
```

3. En Grafana, cada panel de «Resumen» tiene su consulta en el menú del panel › Inspect › Query, sobre las vistas `kpi_*` (`docs/guias/GRAFANA.md`).
4. Las pruebas automáticas (`tests/test_kpi.py`, `tests/test_dashboard.py`, `tests/test_grafana_dashboards.py`) construyen recorridos a mano con resultado conocido y comprueban cada fórmula.

## 5. Lectura de los resultados

Con los 12 recorridos simulados (cada uno con una situación distinta, `13-recorridos-de-prueba.md`) los indicadores se mueven como se espera de la situación: **los recorridos incompletos bajan el cumplimiento de ruta (T1) y las paradas atendidas (T4)**;
**los retrasos suben el retraso promedio (T3) y bajan la puntualidad (T2)**; **los desvíos suben la desviación media (T5) y la diferencia de distancia (T6)**; y la detección correcta (S4) compara lo que cada escenario debía provocar con lo que las reglas detectaron.
Con datos reales la lectura es la misma, pero las cifras serán las de la operación; lo que importa es la tendencia entre periodos y entre líneas, que el tablero muestra junto a cada indicador.
