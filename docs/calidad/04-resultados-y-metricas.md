# Resultados y cuadro de mando de calidad

Generado por `qa/generar_docs.py` con los datos de la ejecución del 23-nov-2026. Las cifras son las mismas del informe en PDF. La interpretación (estabilidad, atípicos, qué falla más) está en el informe, apartado 5.

## 1. Cuadro de mando

| Meta | Umbral | Resultado | Cumple |
|---|---|---|---|
| Pruebas de Odoo aprobadas | 100 % | 100,00 % | Sí |
| Error en la suite en vivo | < 10 % | 0,00 % | Sí |
| Error en la auditoría | < 10 % | 0,00 % | Sí |
| Respuestas HTTP 5xx no esperadas ante cualquier entrada | 0 | 0 | Sí |
| Tiempo promedio de la auditoría | < 0,5 s | 0,0298 s | Sí |
| Latencia p95 con 20 hilos (P2, P7) | < 2 s | 1,6729 s / 1,7149 s | Sí |
| Capacidad de ingesta (100 buses, un reporte cada 10 s) | ≥ 10 req/s | 47,8 req/s | Sí |
| Cobertura de código (sentencias y ramas) | ≥ 80 % | 94,3 % | Sí |
| Cobertura de rutas HTTP | 100 % | 100,0 % | Sí |
| Defectos cerrados | ≥ 90 % | 98,9 % | Sí |
| Posiciones con datos imposibles | 0 | 0 | Sí |
| Integridad concurrente (P6: 20 envíos iguales) | 1 guardada | 1 guardada | Sí |

Se cumplen todas las metas.

## 2. Resultados por conjunto

| Conjunto | Pruebas | Errores | % error |
|---|---|---|---|
| Pruebas de Odoo | 639 | 0 | 0,00 % |
| Suite en vivo | 47 | 0 | 0,00 % |
| Auditoría aleatoria | 1.000 | 0 | 0,00 % |
| Total | 1.686 | 0 | 0,00 % |

## 3. Por tipo de prueba (suite en vivo)

| Tipo | Pruebas | Errores | % error | Media (s) | Desv. est. (s) |
|---|---|---|---|---|---|
| Funcional | 14 | 0 | 0,0 % | 0,1056 | 0,1401 |
| Error | 25 | 0 | 0,0 % | 0,1774 | 0,5477 |
| Rendimiento | 7 | 0 | 0,0 % | 0,1482 | 0,1864 |
| Usabilidad | 1 | 0 | 0,0 % | 0,2782 | 0,0000 |

## 4. Tiempos por escenario

El tiempo es el de la petición, en segundos. El CV (desviación estándar entre media) se usa como criterio de estabilidad: 50 % o menos es "confiable".

| Escenario | N | Media (s) | Máx. (s) | Desv. est. (s) | p95 (s) | CV |
|---|---|---|---|---|---|---|
| Auditoría aleatoria | 1.000 | 0,0298 | 0,1017 | 0,0154 | 0,0593 | 52 % |
| P1 secuencial (100 posiciones) | 100 | 0,0261 | 0,0532 | 0,0091 | 0,0407 | 35 % |
| P2 concurrente (200, 20 hilos) | 200 | 0,3384 | 2,0757 | 0,5653 | 1,6729 | 167 % |
| P3 página /rutas (100) | 100 | 0,0372 | 0,0603 | 0,0095 | 0,0531 | 25 % |
| P4 feed público (45) | 45 | 0,0175 | 0,0357 | 0,0087 | 0,0342 | 50 % |
| P5 salud (100) | 100 | 0,0193 | 0,0382 | 0,0094 | 0,0352 | 49 % |
| P6 duplicados simultáneos (20) | 20 | 0,1183 | 0,1341 | 0,0085 | 0,1327 | 7 % |
| P7 un bus, 20 hilos (60) | 60 | 0,4805 | 2,1568 | 0,6436 | 1,7149 | 134 % |

El servidor de las pruebas corre en un solo proceso. Con 20 hilos simultáneos las peticiones hacen cola y la latencia se dispersa (CV alto) aunque no hay errores; con varios procesos debería bajar, pero no se midió.

## 5. Cobertura de código

Cobertura total: **94,3 %** (4285 sentencias, 171 sin cubrir, 1232 ramas). Archivos con líneas sin cubrir:

| Archivo | Sentencias | Sin cubrir | Cobertura |
|---|---|---|---|
| __manifest__.py | 1 | 1 | 0,0 % |
| controllers/driver_api.py | 281 | 17 | 90,9 % |
| controllers/landing.py | 26 | 3 | 84,4 % |
| controllers/portal.py | 181 | 6 | 95,1 % |
| controllers/stops.py | 18 | 2 | 81,8 % |
| migrations/16.0.1.7.0/post-migrate.py | 11 | 1 | 76,9 % |
| migrations/16.0.1.9.0/pre-migrate.py | 20 | 3 | 87,5 % |
| models/bus_alert.py | 207 | 6 | 95,4 % |
| models/bus_driver_edit.py | 51 | 1 | 95,2 % |
| models/bus_driver_token.py | 61 | 1 | 97,1 % |
| models/bus_fine.py | 273 | 13 | 93,5 % |
| models/bus_fine_detect.py | 338 | 57 | 78,0 % |
| models/bus_fleet.py | 151 | 6 | 95,2 % |
| models/bus_push.py | 95 | 4 | 96,3 % |
| models/bus_report.py | 54 | 1 | 97,1 % |
| models/bus_route.py | 204 | 6 | 96,6 % |
| models/bus_route_gpx.py | 45 | 4 | 87,7 % |
| models/bus_route_record.py | 30 | 1 | 94,7 % |
| models/bus_vehicle.py | 224 | 3 | 97,3 % |
| models/geo.py | 71 | 1 | 97,9 % |
| models/gpx.py | 43 | 3 | 90,2 % |
| models/privacy_text.py | 40 | 5 | 85,9 % |
| models/res_config_settings.py | 57 | 8 | 83,6 % |
| models/res_users.py | 97 | 8 | 89,6 % |
| models/traccar_api.py | 109 | 4 | 95,4 % |
| models/trip_simulator.py | 194 | 1 | 98,8 % |
| models/utils.py | 94 | 5 | 94,6 % |

## 6. Estado de los datos (consultas SQL a la base de pruebas)

| Consulta | Valor |
|---|---|
| Posiciones guardadas (total) | 442 |
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
