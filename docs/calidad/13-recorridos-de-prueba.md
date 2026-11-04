# Recorridos de prueba documentados

Evidencia de la Actividad 5 del proyecto final: al menos 10 recorridos de prueba repartidos entre las rutas, con situaciones normales y de
incumplimiento (puntuales, atrasados, con paradas omitidas, con desvíos). Fecha de la corrida: 2026-11-04.

## 1. Qué son y por qué son simulados

El PDF permite usar datos de prueba **identificados como simulados** cuando no se puede reproducir físicamente un escenario. Estos 12 recorridos lo son:

- Cada recorrido está marcado `simulated = True` y guarda su escenario; pertenecen a buses simulados («Sim L1» a «Sim L4») que ni el mapa en vivo ni las páginas públicas muestran.
- El simulador (`models/trip_simulator.py`) **solo produce posiciones**: las envía por la misma ruta de ingesta que usa el GPS real
  (`bus.vehicle._apply_position`). Lo que fue tarde, omitido o desviado lo deciden las reglas del sistema (`02-estandares-y-reglas.md`, sección 1.1);
  nada del resultado se escribe a mano.
- Cada escenario declara **qué debe detectarse**; la columna «Coincide» compara eso con lo que detectó el sistema. Esa comparación es la métrica de software S4
  (porcentaje de detección correcta de incidencias).
- Los recorridos reales hechos con un celular y Traccar Client se agregan aparte (guía `docs/guias/DEMO-TRACCAR-CLIENT.md`).

## 2. Resultados

| N.º | Ruta | Fecha | Escenario | Qué debía detectarse | Qué detectó el sistema | Coincide | Paradas visitadas / tarde / omitidas | Retraso al final (min) | Distancia estimada / recorrida (km) |
|---|---|---|---|---|---|---|---|---|---|
| 3 | L1 | 2026-11-01 | Adelantado | adelanto | adelanto | Sí | 6 / 0 / 0 | -7 | 4.32 / 4.32 |
| 2 | L1 | 2026-11-02 | Algo tarde, dentro de la tolerancia | ninguna | ninguna | Sí | 6 / 0 / 0 | +1 | 4.32 / 4.32 |
| 1 | L1 | 2026-11-03 | Puntual | ninguna | ninguna | Sí | 6 / 0 / 0 | +0 | 4.32 / 4.32 |
| 6 | L2 | 2026-11-01 | Parada del medio omitida | incompleto, parada omitida | incompleto, parada omitida | Sí | 4 / 0 / 1 | +0 | 11.51 / 11.93 |
| 5 | L2 | 2026-11-02 | Fuera de ruta en el tramo más largo | desvío | desvío | Sí | 5 / 0 / 0 | +0 | 11.51 / 11.96 |
| 4 | L2 | 2026-11-03 | Con retraso | retraso | retraso | Sí | 5 / 4 / 0 | +12 | 11.51 / 11.49 |
| 9 | L3 | 2026-11-01 | Nunca arrancó | incompleto, no arrancó | incompleto, no arrancó | Sí | 0 / 0 / 4 | — | 6.52 / 0.00 |
| 8 | L3 | 2026-11-02 | Se detuvo antes de la última parada | incompleto, parada omitida | incompleto, parada omitida | Sí | 3 / 0 / 1 | +0 | 6.52 / 4.39 |
| 7 | L3 | 2026-11-03 | Puntual | ninguna | ninguna | Sí | 4 / 0 / 0 | +0 | 6.52 / 6.52 |
| 12 | L4 | 2026-11-01 | Puntual | ninguna | ninguna | Sí | 4 / 0 / 0 | +0 | 12.47 / 12.45 |
| 11 | L4 | 2026-11-02 | Exceso de velocidad | velocidad | velocidad | Sí | 4 / 0 / 0 | +0 | 12.47 / 12.45 |
| 10 | L4 | 2026-11-03 | Con retraso y fuera de ruta | retraso, desvío | retraso, desvío | Sí | 4 / 3 / 0 | +14 | 12.47 / 13.09 |

Recorridos simulados: 12. Detección correcta: 12 de 12 (100.0 %).

Qué significa cada columna: «Paradas visitadas / tarde / omitidas» sale de las líneas del recorrido (`bus.trip.stop`); «Retraso al final» es el retraso en la
última parada alcanzada; la distancia estimada es el largo del trazado de la ruta y la recorrida se suma de las posiciones guardadas.

## 3. Cómo se reproduce

```bash
# Odoo de desarrollo con datos de prueba (rutas L1 a L4, minutos previstos y horarios)
docker compose exec -T odoo odoo shell -d buses --no-http --db_host db --db_user odoo --db_password odoo < scripts/dev_seed.py
# los 12 recorridos y este informe
docker compose exec -T odoo odoo shell -d buses --no-http --db_host db --db_user odoo --db_password odoo --log-level=error < scripts/seed_recorridos.py
```

En Odoo: *Configuración > Simulate trips* crea un recorrido de un escenario o el conjunto de 12. Los recorridos quedan en *Operación > Scheduled trips*
(filtro «Simulated»).

## 4. Pruebas automáticas

`tests/test_trip_simulator.py` repite los diez escenarios sobre una ruta de prueba y comprueba que lo detectado es exactamente lo esperado, que el conjunto tiene al menos
10 recorridos en las 4 rutas, y que los buses simulados no aparecen en el mapa en vivo ni en las páginas públicas.
