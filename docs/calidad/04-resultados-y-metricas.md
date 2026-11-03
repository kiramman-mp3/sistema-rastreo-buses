# Resultados y cuadro de mando de calidad

Generado por `qa/generar_docs.py` con los datos de la ejecución del 2-nov-2026. Las cifras son las mismas del informe en PDF. La interpretación (estabilidad, atípicos, qué falla más) está en el informe, apartado 5.

## 1. Cuadro de mando

| Meta | Umbral | Resultado | Cumple |
|---|---|---|---|
| Pruebas de Odoo aprobadas | 100 % | 100,00 % | Sí |
| Error en la suite en vivo | < 10 % | 0,00 % | Sí |
| Error en la auditoría | < 10 % | 0,00 % | Sí |
| Respuestas HTTP 5xx no esperadas ante cualquier entrada | 0 | 0 | Sí |
| Tiempo promedio de la auditoría | < 0,5 s | 0,0442 s | Sí |
| Latencia p95 con 20 hilos (P2, P7) | < 2 s | 1,8679 s / 1,9607 s | Sí |
| Capacidad de ingesta (100 buses, un reporte cada 10 s) | ≥ 10 req/s | 39,9 req/s | Sí |
| Cobertura de código (sentencias y ramas) | ≥ 80 % | 92,8 % | Sí |
| Cobertura de rutas HTTP | 100 % | 100,0 % | Sí |
| Defectos cerrados | ≥ 90 % | 97,1 % | Sí |
| Posiciones con datos imposibles | 0 | 0 | Sí |
| Integridad concurrente (P6: 20 envíos iguales) | 1 guardada | 1 guardada | Sí |

Se cumplen todas las metas.

## 2. Resultados por conjunto

| Conjunto | Pruebas | Errores | % error |
|---|---|---|---|
| Pruebas de Odoo | 250 | 0 | 0,00 % |
| Suite en vivo | 47 | 0 | 0,00 % |
| Auditoría aleatoria | 1.000 | 0 | 0,00 % |
| Total | 1.297 | 0 | 0,00 % |

## 3. Por tipo de prueba (suite en vivo)

| Tipo | Pruebas | Errores | % error | Media (s) | Desv. est. (s) |
|---|---|---|---|---|---|
| Funcional | 14 | 0 | 0,0 % | 0,1369 | 0,1697 |
| Error | 25 | 0 | 0,0 % | 0,2606 | 0,7641 |
| Rendimiento | 7 | 0 | 0,0 % | 0,1800 | 0,2008 |
| Usabilidad | 1 | 0 | 0,0 % | 0,4782 | 0,0000 |

## 4. Tiempos por escenario

El tiempo es el de la petición, en segundos. El CV (desviación estándar entre media) se usa como criterio de estabilidad: 50 % o menos es "confiable".

| Escenario | N | Media (s) | Máx. (s) | Desv. est. (s) | p95 (s) | CV |
|---|---|---|---|---|---|---|
| Auditoría aleatoria | 1.000 | 0,0442 | 0,3474 | 0,0341 | 0,0979 | 77 % |
| P1 secuencial (100 posiciones) | 100 | 0,0393 | 0,0602 | 0,0129 | 0,0566 | 33 % |
| P2 concurrente (200, 20 hilos) | 200 | 0,3960 | 2,0884 | 0,5988 | 1,8679 | 151 % |
| P3 página /rutas (100) | 100 | 0,0685 | 0,1855 | 0,0281 | 0,1169 | 41 % |
| P4 feed público (45) | 45 | 0,0355 | 0,0576 | 0,0105 | 0,0508 | 30 % |
| P5 salud (100) | 100 | 0,0327 | 0,0540 | 0,0122 | 0,0495 | 37 % |
| P6 duplicados simultáneos (20) | 20 | 0,1615 | 0,1783 | 0,0090 | 0,1782 | 6 % |
| P7 un bus, 20 hilos (60) | 60 | 0,5266 | 2,2223 | 0,6567 | 1,9607 | 125 % |

El servidor de las pruebas corre en un solo proceso. Con 20 hilos simultáneos las peticiones hacen cola y la latencia se dispersa (CV alto) aunque no hay errores; con varios procesos debería bajar, pero no se midió.

## 5. Cobertura de código

Cobertura total: **92,8 %** (1853 sentencias, 96 sin cubrir, 494 ramas). Archivos con líneas sin cubrir:

| Archivo | Sentencias | Sin cubrir | Cobertura |
|---|---|---|---|
| __manifest__.py | 1 | 1 | 0,0 % |
| controllers/driver_api.py | 197 | 16 | 87,6 % |
| controllers/landing.py | 24 | 3 | 83,3 % |
| controllers/main.py | 88 | 1 | 96,4 % |
| controllers/portal.py | 174 | 6 | 95,0 % |
| controllers/stops.py | 18 | 2 | 81,8 % |
| models/bus_alert.py | 125 | 14 | 84,9 % |
| models/bus_driver_token.py | 61 | 1 | 97,1 % |
| models/bus_push.py | 81 | 4 | 95,5 % |
| models/bus_route.py | 123 | 4 | 96,1 % |
| models/bus_route_record.py | 30 | 1 | 94,7 % |
| models/bus_vehicle.py | 177 | 14 | 91,7 % |
| models/res_config_settings.py | 44 | 11 | 66,0 % |
| models/res_users.py | 77 | 6 | 88,8 % |
| models/traccar_api.py | 69 | 4 | 92,9 % |
| models/utils.py | 72 | 8 | 88,5 % |

## 6. Estado de los datos (consultas SQL a la base de pruebas)

| Consulta | Valor |
|---|---|
| Posiciones guardadas (total) | 578 |
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
