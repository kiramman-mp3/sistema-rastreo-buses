# Resultados y cuadro de mando de calidad

Generado por `qa/generar_docs.py` con los datos de la ejecución del 28-oct-2026. Las cifras son las mismas del informe en PDF. La interpretación (estabilidad, atípicos, qué falla más) está en el informe, apartado 5.

## 1. Cuadro de mando

| Meta | Umbral | Resultado | Cumple |
|---|---|---|---|
| Pruebas de Odoo aprobadas | 100 % | 100,00 % | Sí |
| Error en la suite en vivo | < 10 % | 7,14 % | Sí |
| Error en la auditoría | < 10 % | 5,70 % | Sí |
| Respuestas HTTP 5xx ante cualquier entrada | 0 | 27 | **No** |
| Tiempo promedio de la auditoría | < 0,5 s | 0,0370 s | Sí |
| Latencia p95 con 20 hilos (P2, P7) | < 2 s | 1,6009 s / 1,9804 s | Sí |
| Capacidad de ingesta (100 buses, un reporte cada 10 s) | ≥ 10 req/s | 39,0 req/s | Sí |
| Cobertura de código (sentencias y ramas) | ≥ 80 % | 93,8 % | Sí |
| Cobertura de rutas HTTP | 100 % | 84,2 % | **No** |
| Defectos cerrados | ≥ 90 % | 70,0 % | **No** |
| Posiciones con datos imposibles | 0 | 33 | **No** |
| Integridad concurrente (P6: 20 envíos iguales) | 1 guardada | 1 guardada | Sí |

Las metas que no se cumplen son las del defecto abierto en la validación de la posición (DEF-008 a DEF-010, ver `05-registro-de-defectos.md`) y la cobertura de tres rutas del panel (`/bus_tracking/track`, `/bus_tracking/stop/load` y `/bus_tracking/stop/save`) que no tienen prueba de petición.

## 2. Resultados por conjunto

| Conjunto | Pruebas | Errores | % error |
|---|---|---|---|
| Pruebas de Odoo | 150 | 0 | 0,00 % |
| Suite en vivo | 42 | 3 | 7,14 % |
| Auditoría aleatoria | 1.000 | 57 | 5,70 % |
| Total | 1.192 | 60 | 5,03 % |

## 3. Por tipo de prueba (suite en vivo)

| Tipo | Pruebas | Errores | % error | Media (s) | Desv. est. (s) |
|---|---|---|---|---|---|
| Funcional | 12 | 0 | 0,0 % | 0,0754 | 0,0333 |
| Error | 22 | 3 | 13,6 % | 0,1431 | 0,3694 |
| Rendimiento | 7 | 0 | 0,0 % | 0,1795 | 0,2120 |
| Usabilidad | 1 | 0 | 0,0 % | 0,4436 | 0,0000 |

## 4. Tiempos por escenario

El tiempo es el de la petición, en segundos. El CV (desviación estándar entre media) se usa como criterio de estabilidad: 50 % o menos es "confiable".

| Escenario | N | Media (s) | Máx. (s) | Desv. est. (s) | p95 (s) | CV |
|---|---|---|---|---|---|---|
| Auditoría aleatoria | 1.000 | 0,0370 | 0,1577 | 0,0175 | 0,0719 | 47 % |
| P1 secuencial (100 posiciones) | 100 | 0,0432 | 0,0716 | 0,0106 | 0,0654 | 24 % |
| P2 concurrente (200, 20 hilos) | 200 | 0,3903 | 2,1447 | 0,5566 | 1,6009 | 143 % |
| P3 página /rutas (100) | 100 | 0,0542 | 0,0897 | 0,0113 | 0,0751 | 21 % |
| P4 feed público (45) | 45 | 0,0278 | 0,0552 | 0,0100 | 0,0469 | 36 % |
| P5 salud (100) | 100 | 0,0328 | 0,0541 | 0,0109 | 0,0517 | 33 % |
| P6 duplicados simultáneos (20) | 20 | 0,1478 | 0,1671 | 0,0107 | 0,1662 | 7 % |
| P7 un bus, 20 hilos (60) | 60 | 0,5607 | 2,0885 | 0,6729 | 1,9804 | 120 % |

El servidor de las pruebas corre en un solo proceso. Con 20 hilos simultáneos las peticiones hacen cola y la latencia se dispersa (CV alto) aunque no hay errores; con varios procesos debería bajar, pero no se midió.

## 5. Cobertura de código

Cobertura total: **93,8 %** (1144 sentencias, 58 sin cubrir, 268 ramas). Archivos con líneas sin cubrir:

| Archivo | Sentencias | Sin cubrir | Cobertura |
|---|---|---|---|
| __manifest__.py | 1 | 1 | 0,0 % |
| controllers/landing.py | 18 | 3 | 77,3 % |
| controllers/main.py | 57 | 5 | 90,1 % |
| controllers/stops.py | 18 | 9 | 40,9 % |
| models/bus_alert.py | 130 | 14 | 85,4 % |
| models/bus_push.py | 74 | 4 | 95,1 % |
| models/bus_route.py | 98 | 3 | 96,6 % |
| models/bus_route_record.py | 25 | 1 | 93,1 % |
| models/bus_vehicle.py | 123 | 4 | 96,3 % |
| models/res_config_settings.py | 24 | 3 | 87,5 % |
| models/traccar_api.py | 64 | 3 | 94,9 % |
| models/utils.py | 47 | 8 | 82,4 % |

## 6. Estado de los datos (consultas SQL a la base de pruebas)

| Consulta | Valor |
|---|---|
| Posiciones guardadas (total) | 478 |
| Posiciones con latitud o longitud fuera de rango | 33 |
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
