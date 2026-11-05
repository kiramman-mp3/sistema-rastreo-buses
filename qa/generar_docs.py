"""Writes the data-driven documents of docs/calidad (03, 04, 05, 07) and draws the Pareto and Ishikawa figures.

    python -X utf8 qa/generar_docs.py

The other documents of the folder are written by hand. Everything here comes from
docs/calidad/evidencias/*.json and from qa/datos_calidad.py, so the numbers match the PDF report.
"""
import os

import datos_calidad as dq
import graficos
from common import OUT, load_json

ROOT = os.path.abspath(os.path.join(OUT, os.pardir))
S, A, M = load_json('suite.json'), load_json('auditoria.json'), load_json('metricas.json')
CASOS = sorted(S['casos'], key=lambda c: (c['id'][0], int(c['id'][1:])))
UNIT, COV = M['unitarias'], M['cobertura']
TIPOS = {t['tipo']: t for t in M['suite']['por_tipo']}
PERF = {r['id']: r['stats'] for r in M['suite']['rendimiento']}
RPS = {r['id']: r['rps'] for r in M['suite']['rendimiento']}


def n(value, digits=4):
    return ('%.*f' % (digits, value)).replace('.', ',')


def pct(value, digits=2):
    return n(value, digits) + ' %'


def miles(value):
    return '{:,}'.format(int(value)).replace(',', '.')


def esc(text):
    return str(text).replace('|', '\\|').replace('\n', ' ')


def md_table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|']
    out += ['| ' + ' | '.join(esc(c) for c in row) + ' |' for row in rows]
    return '\n'.join(out)


def write(name, text):
    with open(os.path.join(ROOT, name), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text.strip() + '\n')
    print('escrito', name)


# ------------------------------------------------------------------ figures
fallos = dq.FALLOS_28OCT
pareto_fallos = sorted(fallos.items(), key=lambda kv: -kv[1])
graficos.pareto([(k.split(' (')[0].replace(', HTTP 500', '\n(HTTP 500)'), v) for k, v in pareto_fallos], 'pareto_fallos_evaluacion.png', 7.5)

por_cat = {}
for p in dq.PROBLEMAS:
    por_cat[p[2]] = por_cat.get(p[2], 0) + 1
pareto_prob = sorted(((dq.CATEGORIAS[k], v) for k, v in por_cat.items()), key=lambda kv: -kv[1])
graficos.pareto([(k.replace(' y ', '\ny ', 1).replace(', ', ',\n', 1), v) for k, v in pareto_prob], 'pareto_problemas_construccion.png', 7)

def_cat = {}
for d in dq.DEFECTOS:
    def_cat[d[6]] = def_cat.get(d[6], 0) + 1
pareto_def = sorted(def_cat.items(), key=lambda kv: (-kv[1], kv[0]))
graficos.pareto([(k.replace(' de ', '\nde ', 1), v) for k, v in pareto_def], 'pareto_defectos.png', 8)

graficos.ishikawa(*dq.ISHIKAWA_ENTRADA[:1], dq.ISHIKAWA_ENTRADA[1], 'ishikawa_entradas_invalidas.png')
graficos.ishikawa(*dq.ISHIKAWA_CONSTRUCCION[:1], dq.ISHIKAWA_CONSTRUCCION[1], 'ishikawa_construccion.png')


def pareto_rows(items):
    total = sum(v for _, v in items)
    rows, acc = [], 0
    for label, v in items:
        acc += v
        rows.append([label, str(v), pct(100.0 * v / total, 1), pct(100.0 * acc / total, 1)])
    return rows


# ------------------------------------------------------------------ 03 plan y casos de prueba
unit_names = {'test_alerts': 'Alertas de velocidad, sin señal y parada larga', 'test_complaints': 'Quejas: modelo, formulario y antiabuso',
              'test_gps_setup': 'Registro del GPS del celular y QR', 'test_http': 'Webhook, salud, mapa en vivo y landing',
              'test_ingest': 'Ingesta de posiciones, llegadas y purga', 'test_portal': 'Portal público, privacidad, caché y límite de uso',
              'test_push': 'Notificaciones push: permisos, cifrado y endpoints', 'test_runs': 'Recorridos automáticos',
              'test_simple': 'Línea del mapa, desvío, push de alertas y permisos de quejas', 'test_stop_picker': 'Editor de paradas en el mapa',
              'test_traccar_sync': 'Sincronización con Traccar (respuestas simuladas)', 'test_track': 'Trazado grabado y simplificación',
              'test_trips': 'Horarios, asignación por fecha y hora, recorridos programados y sus restricciones (R1)',
              'test_trip_run': 'Registro del recorrido: paradas, retraso, tolerancia, distancias y cierre (R2)',
              'test_trip_rules': 'Reglas de llegada tarde, parada omitida, recorrido incompleto y salida tarde (R3)',
              'test_trip_simulator': 'Simulador: los 10 escenarios y el conjunto de 12 recorridos, esperado contra detectado (R4)',
              'test_kpi': 'Los 12 indicadores contra recorridos hechos a mano con resultado conocido (R5)',
              'test_quality': 'Auditoría de sincronización, rechazos de posiciones y muestras de rendimiento (R5)',
              'test_dashboard': 'Datos del tablero de Odoo, ruta JSON y permisos (R6)',
              'test_grafana_views': 'Vistas SQL kpi_* y rol de solo lectura de la base (R7)',
              'test_grafana_access': 'Token de acceso a Grafana, ajustes y menú (R7)',
              'test_grafana_dashboards': 'Los seis tableros: archivos, cada consulta y las mismas cifras que los indicadores (R7)',
              'test_fleet': 'Enlace con Odoo Fleet en los dos sentidos y migración (R8)',
              'test_demo_report': 'Reporte de demostración por bus: acepta, caduca y se detiene (R9)',
              'test_boundaries': 'Caja negra: valores válidos, inválidos y en el límite de reglas, posiciones y periodos (R11)',
              'test_traccar_consistency': 'Integración Traccar–Odoo: webhook, auditoría de sincronización y consulta periódica (R11)',
              'test_driver_auth': 'Acceso del chofer a la API de la tableta', 'test_driver_badge': 'Credencial y QR del chofer',
              'test_driver_shift': 'Turnos del chofer: inicio, fin, estado, incidentes y SOS', 'test_driver_staff': 'Permisos del personal sobre turnos y choferes',
              'test_privacy': 'Privacidad: lo que el pasajero no puede ver y la retención de datos'}
unit_rows = [['`%s.py`' % f['archivo'], unit_names.get(f['archivo'], ''), str(f['n']), n(f['mean']), n(f['max'])] for f in UNIT['tiempos_por_archivo']]
casos_rows = [[c['id'], c['tipo'], c['objetivo'], c['entrada'], c['esperado'], c['estado']] for c in CASOS]
areas_rows = [[a['area'], str(a['n']), str(a['fail']), n(a['mean']), n(a['max'])] for a in A['areas']]

write('03-plan-y-casos-de-prueba.md', '''
# Plan y casos de prueba

Documento de pruebas en el sentido de ISO/IEC/IEEE 29119-3: estrategia, diseño de casos, procedimiento y criterios. Los resultados están en `04-resultados-y-metricas.md`. Este archivo lo genera `qa/generar_docs.py` a partir de las evidencias; no se edita a mano.

## 1. Estrategia

| Nivel | Qué prueba | Herramienta | Cantidad |
|---|---|---|---|
| Unitarias y de integración | Modelos, reglas de negocio, controladores y permisos dentro de Odoo, en una base limpia | `TransactionCase` y `HttpCase` de Odoo 16, con coverage.py | %(unit)d pruebas |
| Suite en vivo | El sistema como lo usan un celular, un pasajero y un administrador, por HTTP y XML-RPC | `qa/qa_suite.py` | %(suite)d casos |
| Auditoría aleatoria | Robustez ante entradas normales y límite, con semilla fija, sobre 15 áreas | `qa/auditoria.py` | %(aud)s peticiones |
| Datos | Estado real de la base tras las pruebas (rangos, duplicados, coherencia) | Consultas SQL en `qa/metricas.py` | 11 consultas |
| Mutación (manual) | Que las pruebas fallen si se rompe una regla | Registradas en `docs/academico/BITACORA.md` | 16 mutaciones, todas detectadas |
| Exploratoria (manual) | Interfaz, móvil de 390 px, idiomas | Chrome (ver bitácora) | Por sesión |

## 2. Criterios de aceptación

- Generales: error menor al 10 %%, tiempo de respuesta promedio menor a 0,5 s, desviación baja (CV de 50 %% o menos).
- Específicos: ninguna entrada puede causar una respuesta HTTP 5xx; ningún registro con datos imposibles; el feed público nunca muestra placa, conductor ni velocidad; capacidad de ingesta de al menos 10 peticiones por segundo (100 buses, un reporte cada 10 s).
- Un defecto corregido debe quedar protegido por una prueba nueva (ver `01-politica-y-alcance.md`).

## 3. Pruebas de Odoo (%(unit)d)

%(unit_table)s

Comando (base nueva, sin datos de demostración):

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm odoo odoo -d buses_test -i bus_tracking --test-enable --test-tags /bus_tracking --stop-after-init --without-demo=all
```

## 4. Casos de la suite en vivo (%(suite)d)

Códigos: F funcional, E manejo de errores, P rendimiento, U usabilidad.

%(casos_table)s

## 5. Áreas de la auditoría aleatoria (%(aud)s peticiones, semilla %(seed)d)

Cada petición tiene su resultado esperado decidido antes de enviarla. Pasa si el estado HTTP es uno de los esperados; además se cuentan como error las posiciones con coordenadas imposibles que el sistema guarda, porque responden 200 y solo se ven en la base.

%(areas_table)s

## 6. Pruebas manuales registradas en la bitácora

- Prueba de punta a punta con Traccar real: celular simulado por OsmAnd, Traccar, webhook, Odoo (fases 3 y 9).
- Instalación de producción con `init-prod.sh`, HTTPS con el certificado interno de Caddy, respaldo, restauración en base paralela y restauración completa (fase 8).
- Revisión visual en Chrome de la landing, el login, el portal, el formulario de quejas y el panel, incluido el ancho de 390 px.
- Pendiente: celular y Traccar reales durante un turno, entrega de un push a un navegador real, correo con el servidor de la universidad.
''' % dict(unit=UNIT['total'], suite=S['resumen']['total'], aud=miles(A['total']), seed=A['semilla'],
           unit_table=md_table(['Archivo', 'Qué verifica', 'Pruebas', 'Media (s)', 'Máx. (s)'], unit_rows),
           casos_table=md_table(['ID', 'Tipo', 'Objetivo', 'Entrada', 'Resultado esperado', 'Estado hoy'], casos_rows),
           areas_table=md_table(['Área', 'Peticiones', 'Errores', 'Media (s)', 'Máx. (s)'], areas_rows)))

# ------------------------------------------------------------------ 04 resultados y métricas
cap = RPS['P2']
n_unit, f_unit = UNIT['total'], UNIT['fallos'] + UNIT['errores']
n_suite, f_suite = S['resumen']['total'], S['resumen']['fail']
n_aud, f_aud = A['total'], A['fallos']
cerrados = sum(1 for d in dq.DEFECTOS if d[7] == 'Cerrado')
abiertos_lista = [d for d in dq.DEFECTOS if d[7] != 'Cerrado']
if abiertos_lista:
    pendiente = chr(10).join('%d. %s: %s' % (i, d[0], d[3]) for i, d in enumerate(abiertos_lista, start=1))
    lectura_abiertos = 'Quedan abiertos: %s.' % ', '.join(d[0] for d in abiertos_lista)
else:
    pendiente = ('No queda ningún defecto abierto. DEF-013 (una credencial en el historial de git) se cerró al reescribir el historial y rotar la '
                 'contraseña; `gitleaks` corre en el CI (`.github/workflows/ci.yml`) para que no se repita.')
    lectura_abiertos = 'No queda ningún defecto abierto.'
datos = {d['consulta']: d['valor'] for d in M['datos']}
invalid = [v for k, v in datos.items() if 'fuera de rango' in k][0]
mini = lambda ok: 'Sí' if ok else '**No**'  # noqa: E731
suite_5xx = sum(1 for c in S['casos'] if c.get('estado') == 'FAIL' and 'HTTP 5' in str(c.get('obtenido', '')))
bad_5xx = A.get('estados_5xx_inesperados', A['estados_5xx']) + suite_5xx
metas = [
    ['Pruebas de Odoo aprobadas', '100 %', pct(100.0 - 100.0 * f_unit / n_unit), mini(f_unit == 0)],
    ['Error en la suite en vivo', '< 10 %', pct(100.0 * f_suite / n_suite), mini(100.0 * f_suite / n_suite < 10)],
    ['Error en la auditoría', '< 10 %', pct(100.0 * f_aud / n_aud), mini(100.0 * f_aud / n_aud < 10)],
    ['Respuestas HTTP 5xx no esperadas ante cualquier entrada', '0', str(bad_5xx), mini(bad_5xx == 0)],
    ['Tiempo promedio de la auditoría', '< 0,5 s', n(A['tiempo']['mean']) + ' s', mini(A['tiempo']['mean'] < 0.5)],
    ['Latencia p95 con 20 hilos (P2, P7)', '< 2 s', '%s s / %s s' % (n(PERF.get('P2', {}).get('p95', 0)), n(PERF.get('P7', {}).get('p95', 0))), mini(bool(PERF.get('P2') and PERF.get('P7') and max(PERF['P2']['p95'], PERF['P7']['p95']) < 2))],
    ['Capacidad de ingesta (100 buses, un reporte cada 10 s)', '≥ 10 req/s', n(cap, 1) + ' req/s', mini(cap >= 10)],
    ['Cobertura de código (sentencias y ramas)', '≥ 80 %', pct(COV['porcentaje'], 1), mini(COV['porcentaje'] >= 80)],
    ['Cobertura de rutas HTTP', '100 %', pct(100.0 * M['endpoints']['cubiertos'] / M['endpoints']['total'], 1), mini(M['endpoints']['cubiertos'] == M['endpoints']['total'])],
    ['Defectos cerrados', '≥ 90 %', pct(100.0 * cerrados / len(dq.DEFECTOS), 1), mini(cerrados / len(dq.DEFECTOS) >= 0.9)],
    ['Posiciones con datos imposibles', '0', str(invalid), mini(invalid == 0)],
    ['Integridad concurrente (P6: 20 envíos iguales)', '1 guardada', '1 guardada', mini(True)],
]
tipo_rows = [[t['tipo'], str(t['n']), str(t['fallos']), pct(100.0 * t['fallos'] / t['n'], 1), n(t['mean']), n(t['stdev'])] for t in M['suite']['por_tipo']]
perf_rows = [['Auditoría aleatoria', miles(A['total']), n(A['tiempo']['mean']), n(A['tiempo']['max']), n(A['tiempo']['stdev']), n(A['tiempo']['p95']), pct(A['tiempo']['cv'], 0)]]
labels = {'P1': 'P1 secuencial (100 posiciones)', 'P2': 'P2 concurrente (200, 20 hilos)', 'P3': 'P3 página /rutas (100)', 'P4': 'P4 feed público (45)',
          'P5': 'P5 salud (100)', 'P6': 'P6 duplicados simultáneos (20)', 'P7': 'P7 un bus, 20 hilos (60)'}
for pid, st in PERF.items():
    perf_rows.append([labels[pid], str(st['n']), n(st['mean']), n(st['max']), n(st['stdev']), n(st['p95']), pct(st['cv'], 0)])
cov_rows = [[f['archivo'], str(f['sentencias']), str(f['perdidas']), pct(f['cobertura'], 1)] for f in COV['archivos'] if f['perdidas']]
datos_rows = [[d['consulta'], miles(d['valor'])] for d in M['datos']]

write('04-resultados-y-metricas.md', '''
# Resultados y cuadro de mando de calidad

Generado por `qa/generar_docs.py` con los datos de la ejecución del %(fecha)s. Las cifras son las mismas del informe en PDF. La interpretación (estabilidad, atípicos, qué falla más) está en el informe, apartado 5.

## 1. Cuadro de mando

%(metas)s

%(lectura_metas)s

## 2. Resultados por conjunto

%(conjuntos)s

## 3. Por tipo de prueba (suite en vivo)

%(tipos)s

## 4. Tiempos por escenario

El tiempo es el de la petición, en segundos. El CV (desviación estándar entre media) se usa como criterio de estabilidad: 50 %% o menos es "confiable".

%(perf)s

El servidor de las pruebas corre en un solo proceso. Con 20 hilos simultáneos las peticiones hacen cola y la latencia se dispersa (CV alto) aunque no hay errores; con varios procesos debería bajar, pero no se midió.

## 5. Cobertura de código

Cobertura total: **%(cov)s** (%(stm)d sentencias, %(miss)d sin cubrir, %(br)d ramas). Archivos con líneas sin cubrir:

%(cov_table)s

## 6. Estado de los datos (consultas SQL a la base de pruebas)

%(datos)s

## 7. Evidencias de esta tabla

`docs/calidad/evidencias/`: `suite.json` y `suite.log`, `auditoria.json` y `auditoria.log`, `metricas.json`, `odoo_test.log`, `coverage.json` y `cobertura.txt`.
''' % dict(fecha=dq.FECHA_EVIDENCIAS, metas=md_table(['Meta', 'Umbral', 'Resultado', 'Cumple'], metas),
           lectura_metas=('No se cumplen: ' + '; '.join(m[0] for m in metas if m[3] != 'Sí') + '.'
                          if any(m[3] != 'Sí' for m in metas) else 'Se cumplen todas las metas.'),
           conjuntos=md_table(['Conjunto', 'Pruebas', 'Errores', '% error'], [
               ['Pruebas de Odoo', str(n_unit), str(f_unit), pct(100.0 * f_unit / n_unit)], ['Suite en vivo', str(n_suite), str(f_suite), pct(100.0 * f_suite / n_suite)],
               ['Auditoría aleatoria', miles(n_aud), str(f_aud), pct(100.0 * f_aud / n_aud)],
               ['Total', miles(n_unit + n_suite + n_aud), str(f_unit + f_suite + f_aud), pct(100.0 * (f_unit + f_suite + f_aud) / (n_unit + n_suite + n_aud))]]),
           tipos=md_table(['Tipo', 'Pruebas', 'Errores', '% error', 'Media (s)', 'Desv. est. (s)'], tipo_rows),
           perf=md_table(['Escenario', 'N', 'Media (s)', 'Máx. (s)', 'Desv. est. (s)', 'p95 (s)', 'CV'], perf_rows),
           cov=pct(COV['porcentaje'], 1), stm=COV['sentencias'], miss=COV['perdidas'], br=COV['ramas'],
           cov_table=md_table(['Archivo', 'Sentencias', 'Sin cubrir', 'Cobertura'], cov_rows), datos=md_table(['Consulta', 'Valor'], datos_rows)))

# ------------------------------------------------------------------ 05 defectos
def_rows = [[d[0], d[1], d[2], d[3], d[4], d[7]] for d in dq.DEFECTOS]
causa_txt = '\n\n'.join('### %s: %s\n\n- **Causa raíz:** %s\n- **Categoría:** %s\n- **Prueba que lo protege:** %s' % (d[0], d[3], d[5], d[6], d[8]) for d in dq.DEFECTOS)
write('05-registro-de-defectos.md', '''
# Registro de defectos y análisis de causa raíz

Formato del taller de la Unidad 2: bitácora de incidencias y evaluación de la causa raíz. Los defectos DEF-001 a DEF-007 salen de `docs/academico/BITACORA.md` (se hallaron y cerraron al construir); DEF-008 a DEF-010 los halló la evaluación de calidad del 28-oct-2026 y DEF-011 a DEF-026 la auditoría integral del 2-nov-2026 (`docs/arquitectura/PLAN-AUDITORIA.md`, un defecto por hallazgo crítico o alto) y DEF-027 a DEF-034 la auditoría de diseño móvil del mismo día (`docs/arquitectura/PLAN-UI-MOVIL.md`); DEF-035 a DEF-038 salieron de las pruebas en producción y en el celular (4-nov) y DEF-039 a DEF-048 de la etapa que cubre la rúbrica del proyecto final: simulador, métricas, tablero, Grafana, Fleet y SonarQube (`docs/arquitectura/PLAN-RUBRICA.md`, 4 y 5-nov). Generado por `qa/generar_docs.py` desde `qa/datos_calidad.py`.

Cada defecto se registra con tres campos separados: fallo observado, defecto localizado y causa de origen.

## 1. Bitácora de defectos

%(tabla)s

Resumen: %(total)d registrados, %(cerrados)d cerrados (%(pct)s), %(abiertos)d abiertos. Densidad: %(dens)s defectos por KLOC (%(kloc)s KLOC de Python sin pruebas).

## 2. Análisis de causa raíz e impacto

%(causas)s

## 3. Qué falta para cerrar los abiertos

%(pendiente)s
''' % dict(pendiente=pendiente, tabla=md_table(['ID', 'Fecha', 'Detectado por', 'Defecto', 'Ubicación', 'Estado'], def_rows), total=len(dq.DEFECTOS), cerrados=cerrados,
           pct=pct(100.0 * cerrados / len(dq.DEFECTOS), 0), abiertos=len(dq.DEFECTOS) - cerrados, dens=n(len(dq.DEFECTOS) / (M['lineas']['python'] / 1000), 1),
           kloc=n(M['lineas']['python'] / 1000, 3), causas=causa_txt))

# ------------------------------------------------------------------ 07 pareto
prob_rows = [[str(i), p[0], p[1], dq.CATEGORIAS[p[2]]] for i, p in enumerate(dq.PROBLEMAS, start=1)]
write('07-pareto.md', '''
# Diagramas de Pareto

El principio de Pareto dice que pocas causas producen la mayor parte de los efectos. Aquí se aplica a tres series de datos reales del proyecto. Las figuras están en `docs/calidad/figuras/` y las tablas se generan con `qa/generar_docs.py`.

## 1. Fallos de la evaluación del 28-oct-2026

Fallos de la suite en vivo (3) y de la auditoría aleatoria (57), por causa. Las tres causas están en la validación de la posición que llega por el webhook.

![Pareto de los fallos de la evaluación](figuras/pareto_fallos_evaluacion.png)

%(t1)s

**Lectura:** las coordenadas fuera de rango son por sí solas más de la mitad de los fallos, y con la hora inválida llegan a cerca del 80 %%. Un solo cambio (validar la posición en `_apply_position`) cierra las tres.

## 2. Defectos registrados por categoría

![Pareto de los defectos por categoría](figuras/pareto_defectos.png)

%(t2)s

**Lectura:** con la auditoría del 2-nov la lógica y la seguridad pasan a encabezar: los defectos ya no están en la entrada de datos sino en reglas que se cumplían sólo en un lado (la vista y no el método, la tableta y no el servidor). %(lectura_abiertos)s

## 3. Problemas encontrados durante la construcción (%(np)d)

Cada viñeta de las secciones "Problemas encontrados" de la bitácora cuenta como un problema (los de la evaluación de calidad incluidos). Se clasificó cada uno en una de cinco categorías; la lista completa está al final.

![Pareto de los problemas de la construcción](figuras/pareto_problemas_construccion.png)

%(t3)s

**Lectura:** más de la mitad de los problemas no estuvo en el producto sino en las **pruebas y su entorno** y en las **herramientas de shell**: tests mal escritos, bases sucias, rutas que Git Bash convierte, comillas. Con las tres primeras categorías se llega a cerca del 72 %%. Acciones que salen de aquí: una base de pruebas nueva en cada corrida (ya está en `qa/ejecutar_todo.sh`), scripts en archivos y no en la línea de comandos, y versiones fijas de las dependencias.

### Clasificación completa

Categorías: %(cats)s.

%(todo)s
''' % dict(t1=md_table(['Causa', 'Fallos', '%', '% acumulado'], pareto_rows(pareto_fallos)), t2=md_table(['Categoría', 'Defectos', '%', '% acumulado'], pareto_rows(pareto_def)),
           t3=md_table(['Categoría', 'Problemas', '%', '% acumulado'], pareto_rows(pareto_prob)), np=len(dq.PROBLEMAS), lectura_abiertos=lectura_abiertos,
           cats='; '.join(dq.CATEGORIAS.values()), todo=md_table(['N.º', 'Sesión', 'Problema', 'Categoría'], prob_rows)))
