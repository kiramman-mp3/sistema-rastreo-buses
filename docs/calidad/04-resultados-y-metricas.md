# Resultados y cuadro de mando de calidad

Generado por `qa/generar_docs.py` con los datos de la ejecución del 28-oct-2026. Las cifras son las mismas del informe en PDF. La interpretación (estabilidad, atípicos, qué falla más) está en el informe, apartado 5.

## 1. Cuadro de mando

| Meta | Umbral | Resultado | Cumple |
|---|---|---|---|
| Pruebas de Odoo aprobadas | 100 % | 100,00 % | Sí |
| Error en la suite en vivo | < 10 % | 2,13 % | Sí |
| Error en la auditoría | < 10 % | 5,70 % | Sí |
| Respuestas HTTP 5xx ante cualquier entrada | 0 | 27 | **No** |
| Tiempo promedio de la auditoría | < 0,5 s | 0,0370 s | Sí |
| Latencia p95 con 20 hilos (P2, P7) | < 2 s | 1,7874 s / 0,0000 s | **No** |
| Capacidad de ingesta (100 buses, un reporte cada 10 s) | ≥ 10 req/s | 28,3 req/s | Sí |
| Cobertura de código (sentencias y ramas) | ≥ 80 % | 93,8 % | Sí |
| Cobertura de rutas HTTP | 100 % | 100,0 % | Sí |
| Defectos cerrados | ≥ 90 % | 96,2 % | Sí |
| Posiciones con datos imposibles | 0 | 1 | **No** |
| Integridad concurrente (P6: 20 envíos iguales) | 1 guardada | 1 guardada | Sí |

Las metas que no se cumplen son las del defecto abierto en la validación de la posición (DEF-008 a DEF-010, ver `05-registro-de-defectos.md`) y la cobertura de tres rutas del panel (`/bus_tracking/track`, `/bus_tracking/stop/load` y `/bus_tracking/stop/save`) que no tienen prueba de petición.

## 2. Resultados por conjunto

| Conjunto | Pruebas | Errores | % error |
|---|---|---|---|
| Pruebas de Odoo | 150 | 0 | 0,00 % |
| Suite en vivo | 47 | 1 | 2,13 % |
| Auditoría aleatoria | 1.000 | 57 | 5,70 % |
| Total | 1.197 | 58 | 4,85 % |

## 3. Por tipo de prueba (suite en vivo)

| Tipo | Pruebas | Errores | % error | Media (s) | Desv. est. (s) |
|---|---|---|---|---|---|
| Funcional | 14 | 0 | 0,0 % | 0,2457 | 0,2490 |
| Error | 25 | 2 | 8,0 % | 0,2716 | 0,5387 |
| Rendimiento | 7 | 1 | 14,3 % | 7,3924 | 19,0053 |
| Usabilidad | 1 | 0 | 0,0 % | 0,9825 | 0,0000 |

## 4. Tiempos por escenario

El tiempo es el de la petición, en segundos. El CV (desviación estándar entre media) se usa como criterio de estabilidad: 50 % o menos es "confiable".

| Escenario | N | Media (s) | Máx. (s) | Desv. est. (s) | p95 (s) | CV |
|---|---|---|---|---|---|---|
| Auditoría aleatoria | 1.000 | 0,0370 | 0,1577 | 0,0175 | 0,0719 | 47 % |
| P1 secuencial (100 posiciones) | 100 | 0,0731 | 0,7275 | 0,0687 | 0,0990 | 94 % |
| P2 concurrente (200, 20 hilos) | 200 | 0,5715 | 2,1768 | 0,6062 | 1,7874 | 106 % |
| P3 página /rutas (100) | 100 | 0,1050 | 0,1644 | 0,0222 | 0,1365 | 21 % |
| P4 feed público (45) | 45 | 0,0428 | 0,0634 | 0,0087 | 0,0571 | 20 % |
| P5 salud (100) | 100 | 0,0456 | 0,0722 | 0,0086 | 0,0596 | 19 % |
| P6 duplicados simultáneos (20) | 20 | 0,4192 | 0,4744 | 0,0340 | 0,4604 | 8 % |

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
| Posiciones guardadas (total) | 375 |
| Posiciones con latitud o longitud fuera de rango | 1 |
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
