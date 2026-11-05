# Resultados y cuadro de mando de calidad

Generado por `qa/generar_docs.py` con los datos de la ejecución del 5-nov-2026. Las cifras son las mismas del informe en PDF. La interpretación (estabilidad, atípicos, qué falla más) está en el informe, apartado 5.

## 1. Cuadro de mando

| Meta | Umbral | Resultado | Cumple |
|---|---|---|---|
| Pruebas de Odoo aprobadas | 100 % | 100,00 % | Sí |
| Error en la suite en vivo | < 10 % | 0,00 % | Sí |
| Error en la auditoría | < 10 % | 0,00 % | Sí |
| Respuestas HTTP 5xx no esperadas ante cualquier entrada | 0 | 0 | Sí |
| Tiempo promedio de la auditoría | < 0,5 s | 0,0363 s | Sí |
| Latencia p95 con 20 hilos (P2, P7) | < 2 s | 1,8955 s / 1,8436 s | Sí |
| Capacidad de ingesta (100 buses, un reporte cada 10 s) | ≥ 10 req/s | 37,1 req/s | Sí |
| Cobertura de código (sentencias y ramas) | ≥ 80 % | 95,9 % | Sí |
| Cobertura de rutas HTTP | 100 % | 100,0 % | Sí |
| Defectos cerrados | ≥ 90 % | 100,0 % | Sí |
| Posiciones con datos imposibles | 0 | 0 | Sí |
| Integridad concurrente (P6: 20 envíos iguales) | 1 guardada | 1 guardada | Sí |

Se cumplen todas las metas.

## 2. Resultados por conjunto

| Conjunto | Pruebas | Errores | % error |
|---|---|---|---|
| Pruebas de Odoo | 544 | 0 | 0,00 % |
| Suite en vivo | 47 | 0 | 0,00 % |
| Auditoría aleatoria | 1.000 | 0 | 0,00 % |
| Total | 1.591 | 0 | 0,00 % |

## 3. Por tipo de prueba (suite en vivo)

| Tipo | Pruebas | Errores | % error | Media (s) | Desv. est. (s) |
|---|---|---|---|---|---|
| Funcional | 14 | 0 | 0,0 % | 0,1429 | 0,2044 |
| Error | 25 | 0 | 0,0 % | 0,2467 | 0,6614 |
| Rendimiento | 7 | 0 | 0,0 % | 0,1919 | 0,2294 |
| Usabilidad | 1 | 0 | 0,0 % | 0,5468 | 0,0000 |

## 4. Tiempos por escenario

El tiempo es el de la petición, en segundos. El CV (desviación estándar entre media) se usa como criterio de estabilidad: 50 % o menos es "confiable".

| Escenario | N | Media (s) | Máx. (s) | Desv. est. (s) | p95 (s) | CV |
|---|---|---|---|---|---|---|
| Auditoría aleatoria | 1.000 | 0,0363 | 0,1586 | 0,0245 | 0,0869 | 68 % |
| P1 secuencial (100 posiciones) | 100 | 0,0335 | 0,0545 | 0,0100 | 0,0482 | 30 % |
| P2 concurrente (200, 20 hilos) | 200 | 0,4200 | 2,1953 | 0,6180 | 1,8955 | 147 % |
| P3 página /rutas (100) | 100 | 0,0707 | 0,1837 | 0,0241 | 0,1116 | 34 % |
| P4 feed público (45) | 45 | 0,0208 | 0,0359 | 0,0074 | 0,0324 | 36 % |
| P5 salud (100) | 100 | 0,0227 | 0,0414 | 0,0078 | 0,0397 | 34 % |
| P6 duplicados simultáneos (20) | 20 | 0,1763 | 0,1893 | 0,0052 | 0,1829 | 3 % |
| P7 un bus, 20 hilos (60) | 60 | 0,5990 | 2,0956 | 0,6835 | 1,8436 | 114 % |

El servidor de las pruebas corre en un solo proceso. Con 20 hilos simultáneos las peticiones hacen cola y la latencia se dispersa (CV alto) aunque no hay errores; con varios procesos debería bajar, pero no se midió.

## 5. Cobertura de código

Cobertura total: **95,9 %** (3086 sentencias, 87 sin cubrir, 860 ramas). Archivos con líneas sin cubrir:

| Archivo | Sentencias | Sin cubrir | Cobertura |
|---|---|---|---|
| __manifest__.py | 1 | 1 | 0,0 % |
| controllers/driver_api.py | 231 | 17 | 88,9 % |
| controllers/landing.py | 24 | 3 | 83,3 % |
| controllers/portal.py | 181 | 6 | 95,1 % |
| controllers/stops.py | 18 | 2 | 81,8 % |
| models/bus_alert.py | 144 | 2 | 97,7 % |
| models/bus_driver_token.py | 61 | 1 | 97,1 % |
| models/bus_fleet.py | 69 | 1 | 96,6 % |
| models/bus_push.py | 81 | 4 | 95,5 % |
| models/bus_route.py | 149 | 6 | 95,8 % |
| models/bus_route_gpx.py | 45 | 4 | 87,7 % |
| models/bus_route_record.py | 30 | 1 | 94,7 % |
| models/bus_vehicle.py | 211 | 6 | 96,1 % |
| models/geo.py | 71 | 1 | 97,9 % |
| models/gpx.py | 43 | 3 | 90,2 % |
| models/privacy_text.py | 40 | 5 | 85,9 % |
| models/res_config_settings.py | 63 | 8 | 85,7 % |
| models/res_users.py | 82 | 6 | 89,5 % |
| models/traccar_api.py | 73 | 4 | 93,3 % |
| models/trip_simulator.py | 146 | 1 | 98,4 % |
| models/utils.py | 80 | 5 | 93,8 % |

## 6. Estado de los datos (consultas SQL a la base de pruebas)

| Consulta | Valor |
|---|---|
| Posiciones guardadas (total) | 374 |
| Posiciones con latitud o longitud fuera de rango | 0 |
| Posiciones con velocidad negativa | 0 |
| Pares (bus, hora GPS) duplicados | 0 |
| Buses con más de una alerta abierta del mismo tipo | 0 |
| Alertas cerradas sin hora de cierre | 0 |
| Recorridos con llegada anterior a la salida | 0 |
| Recorridos terminados sin llegada | 0 |
| Quejas con descripción fuera de 10 a 2000 caracteres | 0 |
| Quejas sin folio asignado | 0 |
| Buses cuyo último estado no coincide con su posición más reciente | 0 |

## 7. Evidencias de esta tabla

`docs/calidad/evidencias/`: `suite.json` y `suite.log`, `auditoria.json` y `auditoria.log`, `metricas.json`, `odoo_test.log`, `coverage.json` y `cobertura.txt`.
