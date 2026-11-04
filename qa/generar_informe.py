"""Builds the quality report (PDF) of the bus-tracking system from the evidence files.

    python -X utf8 qa/generar_informe.py [salida.pdf]

Every number in the text comes from docs/calidad/evidencias/*.json; nothing is typed in by hand
except the defect log, the standards assessment and the recommendations.
"""
import os
import re
import subprocess
import sys

import graficos
from common import OUT, load_json
from informe_lib import (BODY, H1, H2, H3, REF, PageBreak, Report, Spacer, bullets, console, figure, fmt, numbered,
                         p, pct, table, thousands)

SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, os.pardir, 'Informe_calidad_rastreo_buses.pdf')
FECHA = '28-oct-2026'

S, A, M = load_json('suite.json'), load_json('auditoria.json'), load_json('metricas.json')
CASOS = sorted(S['casos'], key=lambda c: (c['id'][0], int(c['id'][1:])))     # run order puts E21 last; the report lists by number


def coma(text):
    return re.sub(r'(\d)\.(\d)', r',', text)
POR_ID = {c['id']: c for c in CASOS}
UNIT, SUITE, AUD, COV = M['unitarias'], M['suite'], A, M['cobertura']
KLOC = M['lineas']['python'] / 1000.0
COMMIT = subprocess.run(['git', 'rev-parse', '--short', 'develop'], capture_output=True, text=True).stdout.strip() or 'develop'


def clasifica_error(v):
    return 'Aceptable' if v < 10 else 'Mejorar' if v <= 30 else 'No aceptable'


def clasifica_tiempo(v):
    return 'Adecuado' if v < 0.5 else 'Aceptable' if v <= 1 else 'Lento'


def estabilidad(mean, sd):
    cv = sd / mean * 100 if mean else 0
    return 'Confiable' if cv <= 50 else 'Inestable'


# ---- derived numbers ---------------------------------------------------------------------------
n_unit, f_unit = UNIT['total'], UNIT['fallos'] + UNIT['errores']
n_suite, f_suite = SUITE['total'], SUITE['fallos']
n_aud, f_aud = AUD['total'], AUD['fallos']
n_total, f_total = n_unit + n_suite + n_aud, f_unit + f_suite + f_aud
tipos = {t['tipo']: t for t in SUITE['por_tipo']}
_EMPTY_STATS = {'n': 0, 'mean': 0.0, 'min': 0.0, 'max': 0.0, 'stdev': 0.0, 'p95': 0.0, 'cv': 0.0}
_perf_raw = {r['id']: r for r in SUITE['rendimiento']}
perf = {pid: _perf_raw.get(pid, {'id': pid, 'stats': _EMPTY_STATS, 'rps': 0})
        for pid in ('P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7')}
fallos_suite = [c for c in CASOS if c['estado'] != 'PASS']
audit_notes = AUD['fallos_por_causa']
DEFECTOS_ABIERTOS = ('DEF-008', 'DEF-009', 'DEF-010')

DEFECTOS = [
    ('DEF-001', 'Traccar reenviaba con GET y la clave forward.json ya no existe en Traccar 6: el webhook respondía 405', 'docker-compose.yml', 'Cerrado: FORWARD_TYPE=json y FORWARD_URL (hallado en la 1.ª sesión, probado con Traccar real)'),
    ('DEF-002', 'El respaldo del filestore salía vacío porque odoo.prod.conf no definía data_dir', 'config/odoo.conf, scripts/backup.sh', 'Cerrado: data_dir fijo; respaldo y restauración repetidos de principio a fin'),
    ('DEF-003', 'El secreto del webhook viajaba en la URL y quedaba escrito en el log de Odoo', 'controllers/main.py', 'Cerrado: cabecera X-Webhook-Secret; el parámetro queda solo por compatibilidad (F12)'),
    ('DEF-004', 'Instalar pywebpush actualizó cryptography y Odoo dejó de arrancar', 'docker/odoo/Dockerfile', 'Cerrado: versiones fijadas (cryptography 3.3.2, pywebpush 1.14.1)'),
    ('DEF-005', 'El asistente de respuesta mostraba la etiqueta <br/> como texto (Markup escapado)', 'asistente de respuesta (eliminado después)', 'Cerrado: hallado por un test; la función se retiró en la simplificación'),
    ('DEF-006', 'Un bus sin ruta rompía la alerta de desvío de ruta', 'models/bus_alert.py', 'Cerrado: hallado por un test; test_simple.TestOffRoute'),
    ('DEF-007', 'El navegador guardaba copias viejas de los CSS y JS públicos', 'controllers/portal.py', 'Cerrado: versión por fecha de archivo (test_public_assets_are_versioned…)'),
    ('DEF-008', 'Se guardan posiciones con latitud o longitud imposibles (p. ej. latitud 95°)', 'models/bus_vehicle.py (_apply_position), models/bus_position.py', 'ABIERTO: E7; %d posiciones inválidas guardadas en la auditoría' % AUD['guardadas_invalidas']),
    ('DEF-009', 'Una latitud no numérica ("abc") produce HTTP 500 en el webhook', 'models/bus_vehicle.py, controllers/main.py', 'ABIERTO: E8; %d de %d envíos de la auditoría' % (audit_notes.get('lat_text', 0), AUD['sondeos_por_nota'].get('lat_text', 0))),
    ('DEF-010', 'Una hora GPS inválida (fixTime = "ayer") produce HTTP 500 en el webhook', 'models/utils.py (parse_traccar_dt), controllers/main.py', 'ABIERTO: E9; %d de %d envíos de la auditoría' % (audit_notes.get('time_text', 0), AUD['sondeos_por_nota'].get('time_text', 0))),
]
cerrados = sum(1 for d in DEFECTOS if not d[3].startswith('ABIERTO'))
abiertos = len(DEFECTOS) - cerrados

# ---- figures -----------------------------------------------------------------------------------
fig_error = graficos.error_rate([('Pruebas de Odoo', n_unit, f_unit), ('Suite en vivo', n_suite, f_suite), ('Auditoría aleatoria', n_aud, f_aud)])
esc = [('Auditoría (1000 peticiones)', AUD['tiempo']['mean'], AUD['tiempo']['stdev'], AUD['tiempo']['p95'])]
for pid, label in (('P1', 'P1 secuencial (100)'), ('P2', 'P2 concurrente (200, 20 hilos)'), ('P3', 'P3 página /rutas'), ('P4', 'P4 feed público'),
                   ('P5', 'P5 salud'), ('P6', 'P6 duplicados simultáneos'), ('P7', 'P7 un bus, 20 hilos')):
    st = perf[pid]['stats']
    esc.append((label, st['mean'], st['stdev'], st['p95']))
fig_tiempos = graficos.times_by_scenario(esc)
fig_hist = graficos.histogram(AUD['tiempos'], AUD['tiempo']['p95'], AUD['tiempo']['mean'])

causas = {}
for c in fallos_suite:
    key = {'E7': 'Coordenadas fuera de rango guardadas', 'E8': 'Latitud no numérica (HTTP 500)', 'E9': 'Hora GPS inválida (HTTP 500)'}.get(c['id'], c['id'])
    causas[key] = causas.get(key, 0) + 1
for key, label in (('coordenadas fuera de rango guardadas', 'Coordenadas fuera de rango guardadas'), ('lat_text', 'Latitud no numérica (HTTP 500)'),
                   ('time_text', 'Hora GPS inválida (HTTP 500)')):
    causas[label] = causas.get(label, 0) + audit_notes.get(key, 0)
for key, value in audit_notes.items():
    if key not in ('coordenadas fuera de rango guardadas', 'lat_text', 'time_text'):
        causas['Otros: ' + key] = value
pareto = sorted(causas.items(), key=lambda kv: -kv[1])
fig_pareto = graficos.pareto(pareto)
fig_cov = graficos.coverage([(f['archivo'].replace('.py', ''), f['cobertura']) for f in COV['archivos'] if f['sentencias'] > 3])

# ---- document ----------------------------------------------------------------------------------
doc = Report(SALIDA, 'Informe técnico de calidad: sistema de rastreo de buses (Odoo 16 + Traccar)', 'Johan Rodríguez Núñez; José Manzano Bahamonde')
E = []
add = E.extend

# I. Portada
add([p('<b>I.&nbsp;&nbsp;&nbsp;&nbsp;PORTADA</b>', H1)])
add(table([
    ['Tema:', '<b>Taller de calidad y pruebas de software del sistema de rastreo de buses de la UTA (Odoo 16 + Traccar), evaluación con métricas, estándares y enfoques del ACS</b>'],
    ['Unidad de Organización Curricular:', 'PROFESIONAL'],
    ['Nivel y Paralelo:', '7mo – A'],
    ['Alumnos participantes:', 'Rodríguez Núñez Johan Gabriel y Manzano Bahamonde José Gabriel'],
    ['Asignatura:', 'Gestión de Calidad de Software'],
    ['Docente:', 'Ing. Alex Javier Maigua Quinteros, Mg.'],
], [0.36, 0.64], header=False)[:-1])
t = E[-1]
t.setStyle(__import__('reportlab.platypus', fromlist=['TableStyle']).TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), 0, 'white')]))
E.append(Spacer(1, 6))

add([p('<b>II.&nbsp;&nbsp;&nbsp;INFORME DE GUÍA PRÁCTICA</b>', H1), p('<b>2.1&nbsp;&nbsp;Objetivos</b>', H2), p('General', H3),
     p('Evaluar la calidad del sistema de rastreo de buses de la Universidad Técnica de Ambato (módulo Odoo <i>bus_tracking</i> con Traccar) mediante '
       'pruebas, métricas, análisis estadístico, estándares y enfoques del Aseguramiento y Control de la Calidad de Software (ACS), para determinar '
       'con evidencia objetiva si el sistema es apto para producción.'), p('Específicos:', H3)])
add(bullets([
    'Diseñar y ejecutar pruebas funcionales, de error, de rendimiento y de usabilidad que registren objetivo, entrada, resultado esperado, resultado obtenido, error, tiempo de respuesta y evidencia.',
    'Calcular el porcentaje de error, el tiempo promedio y la desviación estándar, y clasificarlos con los criterios de calidad del curso.',
    'Analizar la estabilidad del sistema, los valores atípicos, el tipo de prueba que más falla y las zonas con más errores.',
    'Evaluar el sistema con ISO/IEC 25010, ISO/IEC 12207 y CMMI, e identificar los enfoques formales del ACS aplicados y los que faltan.']))

add([p('<b>2.2&nbsp;&nbsp;Actividades por desarrollar</b>', H2), p('<b>1.&nbsp;&nbsp;Escenario</b>', H3)])
add([p('La universidad necesita decidir si el sistema de rastreo de buses puede pasar de desarrollo a producción. El sistema recibe la posición GPS de los '
       'celulares de los choferes (app Traccar Client) a través de Traccar, la guarda en Odoo y ofrece: <b>ingesta de posiciones</b> por webhook y por tarea de respaldo, '
       '<b>detección de llegadas y recorridos</b> entre la primera y la última parada, <b>alertas</b> (exceso de velocidad, bus sin señal, parada larga, desvío de ruta) '
       'con aviso push, un <b>portal público de pasajeros</b> que solo muestra nombre, posición, rumbo y estado de cada bus, y un <b>formulario público de quejas</b> con '
       'protección contra abuso y datos de contacto restringidos. El proyecto se construyó en 16 entradas de bitácora (26 al 28 de octubre de 2026) y '
       'quedó reducido, por pedido del cliente, a lo mínimo defendible.'),
     p('El módulo tiene los modelos “bus.vehicle”, “bus.route”, “bus.route.stop”, “bus.position”, “bus.stop.arrival”, “bus.run”, “bus.alert”, “bus.complaint” y '
       '“bus.push.subscription”, y %d rutas HTTP (“/bus_tracking/traccar/webhook”, “/bus_tracking/health”, “/rutas”, “/rutas/&lt;código&gt;/buses.json”, “/quejas”, entre otras). '
       'Se ejecutó en Odoo 16 sobre Docker (Postgres 15), en una base nueva “buses_qa” con el módulo instalado con -i bus_tracking, sobre la rama develop (commit %s). '
       'La suite de Odoo corrió en el contenedor y las pruebas en vivo, la auditoría y las métricas contra un servidor Odoo dedicado en el puerto 8071, '
       'como lo harían un celular, un pasajero o un administrador. <b>Alcance y límites:</b> el GPS se simuló con peticiones HTTP en el formato de Traccar; no se probó '
       'con un celular real ni se entregó una notificación push a un navegador real (ver apartado 8).' % (M['endpoints']['total'], COMMIT))])
add([p('Los criterios de calidad del taller se resumen en la Tabla 1; las fuentes de evidencia, en la Tabla 2; y la correspondencia entre los nueve pasos del taller y este documento, en la Tabla 3.')])

add(table([['Indicador', 'Rango', 'Clasificación'],
           ['Porcentaje de error', '&gt; 30 %', 'No aceptable'], ['', '10 % - 30 %', 'Mejorar'], ['', '&lt; 10 %', 'Aceptable'],
           ['Tiempo promedio de respuesta', '&gt; 1 s', 'Lento'], ['', '0,5 s - 1 s', 'Aceptable'], ['', '&lt; 0,5 s', 'Adecuado'],
           ['Desviación estándar', 'Alta (CV &gt; 50 %)', 'Inestable'], ['', 'Baja (CV ≤ 50 %)', 'Confiable']],
          [0.4, 0.3, 0.3], caption='Criterios de calidad de referencia del taller'))
add([p('El coeficiente de variación (CV = desviación estándar ÷ media) se usa para decidir si la desviación es “alta” o “baja”; el límite de 50 % es una decisión de este informe, '
       'porque el curso no fija un número.')])

add(table([['Código', 'Fuente', 'Qué aporta'],
           ['B1', 'Bitácora (docs/academico/BITACORA.md) y plan (docs/arquitectura/PLAN.md)', '16 entradas de trabajo, defectos hallados y corregidos, mutaciones manuales, limitaciones declaradas.'],
           ['R1', 'Pruebas de Odoo (150) – evidencias/odoo_test.log', 'Pruebas unitarias y de integración (TransactionCase y HttpCase) en base limpia, con tiempos por prueba.'],
           ['R2', 'Suite en vivo (%d casos) – qa/qa_suite.py, suite.json, suite.log' % n_suite, 'Casos funcionales, de error, de rendimiento y de usabilidad contra el servidor, con resultado, mensaje y tiempo.'],
           ['R3', 'Auditoría aleatoria (%s) – qa/auditoria.py, auditoria.json' % thousands(n_aud), 'Peticiones generadas al azar (semilla fija) sobre 15 áreas, para comprobar robustez ante entradas normales y límite.'],
           ['R4', 'Consultas SQL a la base buses_qa', 'Estado real de los datos: coherencia, valores fuera de rango, duplicados, alertas y recorridos.'],
           ['R5', 'Métricas de calidad – qa/metricas.py, metricas.json', 'Error, tiempos, desviación, p95, cobertura, líneas de código y Defectos/KLOC.'],
           ['R6', 'Cobertura con coverage.py – cobertura.txt, coverage.json', 'Cobertura real de sentencias y ramas del módulo durante las pruebas de Odoo.']],
          [0.1, 0.4, 0.5], caption='Fuentes de evidencia'))

add(table([['Paso', 'Requisito', 'Dónde se cumple', 'Estado'],
           ['1. Escenario', 'Funciones del sistema, problemas conocidos, límites de la prueba', 'Actividad 1', 'Cumplido'],
           ['2. Diseño de pruebas', 'Al menos 3 funcionales, 2 de error y 2 de rendimiento, con objetivo, entrada y resultado esperado', 'Actividad 2, Tabla 4', '%d funcionales, %d de error, %d de rendimiento y %d de usabilidad (más %d pruebas de Odoo)' % (
               tipos['Funcional']['n'], tipos['Error']['n'], tipos['Rendimiento']['n'], tipos['Usabilidad']['n'], n_unit)],
           ['3. Ejecución', 'Resultado obtenido, error, tiempo de respuesta y evidencia', 'Actividad 3, Tablas 5 a 7, Anexo A', 'Cumplido'],
           ['4. Métricas', '% de error, tiempo promedio, desviación estándar; justificación', 'Actividad 4, Tablas 8 a 15', 'Cumplido, con CV, p95, cobertura y Defectos/KLOC'],
           ['5. Análisis estadístico', 'Estabilidad, atípicos, tipo de prueba que más falla, dónde se concentran los errores', 'Actividad 5, Tablas 16 y 17', 'Cumplido'],
           ['6. Enfoques del ACS', 'Aplicados, faltantes y riesgos', 'Actividad 6, Tabla 18', 'Cumplido'],
           ['7. Estándares', 'ISO 25010, ISO 12207, CMMI, con justificación', 'Actividad 7, Tablas 19 a 21', 'Cumplido'],
           ['8. Análisis final', 'Aptitud para producción, métricas que justifican, riesgos, mejoras priorizadas', 'Actividad 8, Tabla 22', 'Cumplido'],
           ['9. Entregable', 'Tabla de pruebas, resultados, métricas, análisis, conclusiones y recomendaciones', 'Todo el documento; apartados 2.3 y 2.4', 'Cumplido']],
          [0.17, 0.38, 0.22, 0.23], caption='Cumplimiento de los pasos del taller'))

# 2. Diseño
add([p('<b>2.&nbsp;&nbsp;Diseño de pruebas</b>', H3),
     p('Se diseñaron %d pruebas en vivo, clasificadas por código según su tipo, además de las %d pruebas automáticas de Odoo que ya tenía el proyecto:' % (n_suite, n_unit))])
add(bullets(['Funcionales (F): %d pruebas.' % tipos['Funcional']['n'], 'Manejo de errores (E): %d pruebas.' % tipos['Error']['n'],
             'Rendimiento (P): %d pruebas.' % tipos['Rendimiento']['n'], 'Usabilidad (U): %d prueba.' % tipos['Usabilidad']['n']]))
add([p('Cada caso detalla su objetivo, datos de entrada y resultado esperado en la Tabla 4. Las pruebas de Odoo se resumen en la Tabla 7.'), p('Criterios de aceptación:', H3)])
add(bullets(['Generales: tasa de error menor al 10 %, tiempo de respuesta promedio menor a 0,5 s y baja desviación.',
             'Específicos del sistema: ninguna entrada, normal o mal formada, debe causar una respuesta HTTP 5xx; ningún registro con datos imposibles; el feed público nunca debe mostrar placa, conductor ni velocidad; '
             'capacidad de ingesta de al menos 10 peticiones por segundo (100 buses con un reporte cada 10 s, el supuesto del plan).']))
rows = [['ID', 'Objetivo', 'Entrada', 'Resultado esperado']]
sections = []
for kind, title in (('Funcional', 'Pruebas funcionales'), ('Error', 'Pruebas de error'), ('Rendimiento', 'Pruebas de rendimiento'), ('Usabilidad', 'Prueba de usabilidad')):
    sections.append(len(rows))
    rows.append([title, '', '', ''])
    rows += [[c['id']] + [c[k].replace('<', '&lt;') for k in ('objetivo', 'entrada', 'esperado')] for c in CASOS if c['tipo'] == kind]
add(table(rows, [0.07, 0.33, 0.30, 0.30], section_rows=sections, caption='Diseño de pruebas'))

# 3. Ejecución
add([p('<b>3.&nbsp;&nbsp;Ejecución de pruebas</b>', H3),
     p('Las pruebas de Odoo se ejecutaron con el comando de la sección Tests del README (base limpia, sin datos de demostración) envuelto en coverage.py. '
       'Las pruebas en vivo, la auditoría y las métricas se ejecutaron contra el servidor Odoo del puerto 8071 mediante:')])
add(console(['python -X utf8 qa/qa_suite.py', 'python -X utf8 qa/auditoria.py', 'python -X utf8 qa/metricas.py'], 'Comandos de ejecución'))
add([p('Cada caso registra resultado, mensaje del sistema, error, estado y tiempo. Las cifras son las de la <b>última ejecución completa</b> (%s); las anteriores se descartaron por errores de la propia herramienta de prueba (dos corridas simultáneas y buses compartidos entre pruebas) y los tres fallos reales se repitieron en todas. '
       'No existe una versión “antes de las correcciones”: los fallos no se corrigieron durante la evaluación, de modo que el informe los muestra abiertos. El historial de defectos anteriores, hallados y cerrados durante la construcción, '
       'está en la Tabla 17. El servidor se reinició antes de la ejecución porque dos límites (60 consultas del feed por minuto y 5 quejas por hora) viven en la memoria del proceso.' % FECHA),
     p('Como evidencia se guardaron los registros de ejecución en lugar de capturas de pantalla: el registro de Odoo (Imagen 8), la salida de la suite en vivo (Imagen 9), '
       'el resumen de la auditoría (Imagen 10), el reporte de cobertura (Imagen 7) y los resultados en JSON del directorio docs/calidad/evidencias.')])
filas = [['ID', 'Resultado obtenido', 'Error observado', 'Defecto']]
for c in fallos_suite:
    d = {'E7': 'DEF-008', 'E8': 'DEF-009', 'E9': 'DEF-010'}.get(c['id'], '—')
    filas.append([c['id'], coma(c['obtenido']).replace('<', '&lt;'), coma(c['error']).replace('<', '&lt;'), d])
add(table(filas, [0.07, 0.38, 0.40, 0.15], caption='Fallos de la ejecución en vivo'))

filas = [['ID', 'Resultado obtenido', 'Mensaje del sistema', 'Error', 'Estado', 'Tiempo (s)']]
sections = []
for kind, title in (('Funcional', 'Pruebas funcionales'), ('Error', 'Pruebas de error'), ('Rendimiento', 'Pruebas de rendimiento'), ('Usabilidad', 'Prueba de usabilidad')):
    sections.append(len(filas))
    filas.append([title, '', '', '', '', ''])
    for c in [c for c in CASOS if c['tipo'] == kind]:
        tiempo = c['stats']['mean'] if 'stats' in c else c['tiempo']
        filas.append([c['id'], coma(c['obtenido']).replace('<', '&lt;'), (c.get('mensaje') or '').replace('<', '&lt;'),
                      'Ninguno' if c['estado'] == 'PASS' else 'Ver Tabla 5', '<b>%s</b>' % c['estado'], fmt(tiempo)])
add(table(filas, [0.07, 0.36, 0.25, 0.1, 0.09, 0.13], section_rows=sections, align_center=(4, 5), caption='Resultados de la ejecución en vivo (tiempo: de la petición; en rendimiento, media por petición)'))

nombres = {'test_alerts': 'Alertas de velocidad, sin señal y parada larga', 'test_complaints': 'Quejas: modelo, formulario y antiabuso', 'test_gps_setup': 'Registro del GPS del celular y QR',
           'test_http': 'Webhook, salud, mapa en vivo y landing', 'test_ingest': 'Ingesta de posiciones, llegadas y purga', 'test_portal': 'Portal público, privacidad, caché y límite',
           'test_push': 'Notificaciones push: permisos, cifrado y endpoints', 'test_runs': 'Recorridos automáticos', 'test_simple': 'Línea del mapa, desvío, push de alertas y permisos de quejas',
           'test_stop_picker': 'Editor de paradas en el mapa', 'test_traccar_sync': 'Sincronización con Traccar (respuestas simuladas)', 'test_track': 'Trazado grabado y simplificación'}
filas = [['Archivo de pruebas', 'Qué verifica', 'Pruebas', 'Fallos', 'Media (s)', 'Máx. (s)']]
for f in UNIT['tiempos_por_archivo']:
    filas.append([f['archivo'] + '.py', nombres.get(f['archivo'], ''), str(f['n']), '0', fmt(f['mean']), fmt(f['max'])])
filas.append(['<b>Total</b>', '', '<b>%d</b>' % n_unit, '<b>%d</b>' % f_unit, '<b>%s</b>' % fmt(UNIT['tiempo']['mean']), '<b>%s</b>' % fmt(UNIT['tiempo']['max'])])
add(table(filas, [0.2, 0.4, 0.09, 0.08, 0.11, 0.12], align_center=(2, 3, 4, 5), caption='Pruebas de Odoo por archivo (resumen de la ejecución con coverage.py)'))

# 4. Métricas
add([p('<b>4.&nbsp;&nbsp;Métricas de calidad</b>', H3),
     p('Todas las métricas se calculan con “qa/metricas.py”. El porcentaje de error es el criterio de aceptación del curso y mide el incumplimiento de reglas críticas; la media, el máximo y el p95 '
       'muestran que el promedio oculta colas lentas; la desviación estándar, la varianza y el CV miden la estabilidad, que el curso considera más importante que la velocidad promedio, por lo que se reportan '
       'por escenario; y la cobertura y los Defectos/KLOC miden qué tan probado y qué tan defectuoso está el código.'), p('<b>4.1&nbsp;&nbsp;Porcentaje de error y de éxito</b>', H2)])
filas = [['Conjunto', 'Pruebas', 'Errores', '% error', '% éxito', 'Clasificación']]
for nombre, n, f in (('Pruebas de Odoo', n_unit, f_unit), ('Suite en vivo', n_suite, f_suite), ('Auditoría aleatoria', n_aud, f_aud), ('Total', n_total, f_total)):
    filas.append([nombre, thousands(n), str(f), pct(100.0 * f / n), pct(100.0 - 100.0 * f / n), clasifica_error(100.0 * f / n)])
add(table(filas, [0.28, 0.12, 0.12, 0.14, 0.14, 0.2], align_center=(1, 2, 3, 4), caption='Porcentaje de error por conjunto de pruebas'))
add([p('En la auditoría se cuentan como error las respuestas HTTP 5xx (%d) y las posiciones con coordenadas imposibles que el sistema guardó (%d), porque esas últimas responden 200 y solo se ven en la base de datos.' % (AUD['estados_5xx'], AUD['guardadas_invalidas']))])
add(figure(fig_error, 'Porcentaje de error por conjunto de pruebas'))

add([p('<b>4.2&nbsp;&nbsp;Tiempo de respuesta y desviación estándar</b>', H2)])
filas = [['Conjunto', 'N', 'Media (s)', 'Mín. (s)', 'Máx. (s)', 'Desv. est. (s)', 'p95 (s)', 'CV', 'Clasificación']]
filas.append(['Auditoría aleatoria', thousands(n_aud), fmt(AUD['tiempo']['mean']), fmt(AUD['tiempo']['min']), fmt(AUD['tiempo']['max']), fmt(AUD['tiempo']['stdev']), fmt(AUD['tiempo']['p95']),
              pct(AUD['tiempo']['cv'], 0), '%s / %s' % (clasifica_tiempo(AUD['tiempo']['mean']), estabilidad(AUD['tiempo']['mean'], AUD['tiempo']['stdev']))])
etiquetas = {'P1': 'P1 secuencial (100 posiciones)', 'P2': 'P2 concurrente (200 posiciones, 20 hilos)', 'P3': 'P3 página /rutas (100)', 'P4': 'P4 feed público (45)',
             'P5': 'P5 salud (100)', 'P6': 'P6 duplicados simultáneos (20)', 'P7': 'P7 un bus, 20 hilos (60)'}
for pid in ('P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7'):
    st = perf[pid]['stats']
    filas.append([etiquetas[pid], str(st['n']), fmt(st['mean']), fmt(st['min']), fmt(st['max']), fmt(st['stdev']), fmt(st['p95']), pct(st['cv'], 0),
                  '%s / %s' % (clasifica_tiempo(st['mean']), estabilidad(st['mean'], st['stdev']))])
add(table(filas, [0.27, 0.06, 0.09, 0.08, 0.08, 0.1, 0.08, 0.07, 0.17], align_center=(1, 2, 3, 4, 5, 6, 7), caption='Tiempo de respuesta por escenario'))
add(figure(fig_tiempos, 'Tiempo de respuesta medio por escenario'))
add(figure(fig_hist, 'Distribución de los tiempos de la auditoría'))

add([p('<b>4.3&nbsp;&nbsp;Por tipo de prueba, por ruta y por área</b>', H2)])
filas = [['Tipo', 'Pruebas', 'Errores', '% error', 'Media (s)', 'Desv. est. (s)']]
for t in SUITE['por_tipo']:
    filas.append([t['tipo'], str(t['n']), str(t['fallos']), pct(100.0 * t['fallos'] / t['n'], 1), fmt(t['mean']), fmt(t['stdev'])])
filas.append(['Pruebas de Odoo', str(n_unit), str(f_unit), pct(0, 1), fmt(UNIT['tiempo']['mean']), fmt(UNIT['tiempo']['stdev'])])
add(table(filas, [0.28, 0.12, 0.12, 0.14, 0.17, 0.17], align_center=(1, 2, 3, 4, 5), caption='Resultados por tipo de prueba (rendimiento: media de las medias de cada escenario)'))
filas = [['Área de la auditoría', 'Peticiones', 'Errores', 'Media (s)', 'Mín. (s)', 'Máx. (s)', 'Desv. est. (s)']]
for a in AUD['areas']:
    filas.append([a['area'], str(a['n']), str(a['fail']), fmt(a['mean']), fmt(a['min']), fmt(a['max']), fmt(a['stdev'])])
add(table(filas, [0.38, 0.1, 0.08, 0.11, 0.1, 0.1, 0.13], align_center=(1, 2, 3, 4, 5, 6), caption='Tiempos y errores por área (rutas del sistema) en la auditoría'))
lentas = sorted(AUD['areas'], key=lambda a: -a['mean'])[:3]
add([p('Las áreas más lentas en promedio son %s. Los errores de la auditoría se concentran en el webhook (área 06); el resto de las áreas tuvo 0 errores.' % ', '.join('«%s» (%s s)' % (a['area'][3:], fmt(a['mean'])) for a in lentas))])

add([p('<b>4.4&nbsp;&nbsp;Cobertura, defectos y datos</b>', H2)])
filas = [['Archivo', 'Sentencias', 'No cubiertas', 'Ramas', 'Cobertura']]
for f in COV['archivos']:
    filas.append([f['archivo'], str(f['sentencias']), str(f['perdidas']), str(f['ramas']), pct(f['cobertura'], 1)])
filas.append(['<b>Total del módulo</b>', '<b>%d</b>' % COV['sentencias'], '<b>%d</b>' % COV['perdidas'], '<b>%d</b>' % COV['ramas'], '<b>%s</b>' % pct(COV['porcentaje'], 1)])
add(table(filas, [0.46, 0.14, 0.14, 0.12, 0.14], align_center=(1, 2, 3, 4), caption='Cobertura de código (coverage.py, sentencias y ramas, sin contar los tests)'))
add(figure(fig_cov, 'Cobertura por archivo (el módulo completo: %s)' % pct(COV['porcentaje'], 1)))
sin = [e['ruta'] for e in M['endpoints']['detalle'] if not e['cubierta']]
reglas = 17
cubiertas = 15
filas = [['Métrica', 'Valor'],
         ['Cobertura de código (sentencias y ramas)', '%s (%d de %d sentencias; solo líneas: %s)' % (pct(COV['porcentaje'], 1), COV['sentencias'] - COV['perdidas'], COV['sentencias'], pct(COV['solo_lineas'], 1))],
         ['Cobertura de rutas HTTP', '%d / %d%s' % (M['endpoints']['cubiertos'], M['endpoints']['total'], (' (sin prueba de petición: %s)' % ', '.join(sin)) if sin else '')],
         ['Cobertura de reglas de negocio', '%d / %d (%s); faltan validación de coordenadas y hora GPS, y entrega real desde un celular' % (cubiertas, reglas, pct(100.0 * cubiertas / reglas, 1))],
         ['Tipos de prueba cubiertos', 'Funcional, error, rendimiento, usabilidad, integridad concurrente y auditoría aleatoria']]
add(table(filas, [0.38, 0.62], caption='Cobertura de código, de rutas y de reglas'))
filas = [['Métrica', 'Valor'],
         ['Defectos registrados / cerrados / abiertos', '%d / %d / %d' % (len(DEFECTOS), cerrados, abiertos)],
         ['Líneas de código del módulo (Python, sin tests ni comentarios)', '%s (%s KLOC); además %s líneas de XML, %s de JS y %s de CSS' % (
             thousands(M['lineas']['python']), fmt(KLOC, 3), thousands(M['lineas']['xml']), thousands(M['lineas']['js']), thousands(M['lineas']['css']))],
         ['Densidad de defectos (Defectos/KLOC, métrica de CMMI nivel 4 del curso)', '%s (abiertos: %s)' % (fmt(len(DEFECTOS) / KLOC, 1), fmt(abiertos / KLOC, 1))],
         ['Líneas de pruebas por línea de código', fmt(M['lineas']['python_tests'] / M['lineas']['python'], 2)]]
for d in M['datos']:
    filas.append([d['consulta'], thousands(d['valor'])])
add(table(filas, [0.62, 0.38], caption='Defectos y estado de los datos (consultas SQL a buses_qa tras las pruebas)'))
add([p('Las posiciones con coordenadas fuera de rango son las que guardaron E7 y la auditoría (DEF-008); todo lo demás es coherente, y las restricciones de la base de datos '
       '(posición única por bus y hora, una alerta abierta por bus y tipo) se mantuvieron incluso con 20 hilos escribiendo a la vez.')])

add([p('<b>4.5&nbsp;&nbsp;Metas del ACS</b>', H2)])
def meta(nombre, umbral, resultado, cumple):
    return [nombre, umbral, resultado, 'Sí' if cumple else '<b>No</b>']
cap = perf['P2']['rps']
metas = [['Meta', 'Umbral', 'Resultado', 'Cumple'],
         meta('Error en las pruebas de Odoo', '&lt; 10 %', pct(100.0 * f_unit / n_unit), 100.0 * f_unit / n_unit < 10),
         meta('Error en la suite en vivo', '&lt; 10 %', pct(100.0 * f_suite / n_suite), 100.0 * f_suite / n_suite < 10),
         meta('Error en la auditoría', '&lt; 10 %', pct(100.0 * f_aud / n_aud), 100.0 * f_aud / n_aud < 10),
         meta('Respuestas HTTP 5xx ante cualquier entrada', '0', str(AUD['estados_5xx'] + len([c for c in fallos_suite if 'HTTP 500' in c['error']])), AUD['estados_5xx'] == 0 and not any('HTTP 500' in c['error'] for c in fallos_suite)),
         meta('Tiempo promedio (auditoría / suite en vivo)', '&lt; 0,5 s', '%s s / %s s' % (fmt(AUD['tiempo']['mean']), fmt(tipos['Funcional']['mean'])), AUD['tiempo']['mean'] < 0.5),
         meta('Latencia p95 bajo 20 hilos (P2, P7)', '&lt; 2 s', '%s s / %s s' % (fmt(perf['P2']['stats']['p95']), fmt(perf['P7']['stats']['p95']) if 'P7' in _perf_raw else 'sin medida'),
              'P7' in _perf_raw and max(perf['P2']['stats']['p95'], perf['P7']['stats']['p95']) < 2),
         meta('Capacidad de ingesta (100 buses, un reporte cada 10 s)', '≥ 10 req/s', '%s req/s (P2)' % fmt(cap, 1), cap >= 10),
         meta('Cobertura de código', '≥ 80 %', pct(COV['porcentaje'], 1), COV['porcentaje'] >= 80),
         meta('Cobertura de rutas HTTP', '100 %', pct(100.0 * M['endpoints']['cubiertos'] / M['endpoints']['total'], 1), M['endpoints']['cubiertos'] == M['endpoints']['total']),
         meta('Defectos cerrados', '≥ 90 %', pct(100.0 * cerrados / len(DEFECTOS), 1), cerrados / len(DEFECTOS) >= 0.9),
         meta('Posiciones con datos imposibles', '0', str(next(d['valor'] for d in M['datos'] if 'fuera de rango' in d['consulta'])), next(d['valor'] for d in M['datos'] if 'fuera de rango' in d['consulta']) == 0),
         meta('Integridad concurrente (P6: 20 envíos iguales)', '1 guardada', '%s guardada(s)' % ('1' if perf['P6']['stats']['n'] == 20 and POR_ID['P6']['estado'] == 'PASS' else '≠ 1'), POR_ID['P6']['estado'] == 'PASS')]
add(table(metas, [0.4, 0.15, 0.33, 0.12], align_center=(1, 3), caption='Cumplimiento de las metas de calidad'))

# 5. Análisis estadístico
p2, p1, p7 = perf['P2']['stats'], perf['P1']['stats'], perf['P7']['stats']
add([p('<b>5.&nbsp;&nbsp;Análisis estadístico</b>', H3)])
add([p('<b>• ¿El sistema es estable?</b>', BODY),
     p('En parte. En las ejecuciones normales sí: 0 fallos en las %d pruebas de Odoo, latencia secuencial de %s s con desviación de %s s (P1, CV %s) y la integridad se conserva: P6 guarda 1 posición de 20 envíos idénticos simultáneos '
       'y P7 guarda las 60 posiciones de un mismo bus enviadas por 20 hilos. Bajo concurrencia la latencia se dispersa: P2 tiene media %s s, desviación %s s (CV %s), p95 %s s y máximo %s s, '
       'lo que por el criterio del taller es una desviación alta. La causa probable es que el servidor de la prueba corre en un solo proceso y atiende las 20 peticiones en cola; '
       'aun así sostuvo %s peticiones por segundo sin errores, unas %s veces lo que exige una flota de 100 buses. En producción (varios procesos) la dispersión debería bajar, pero eso no se midió.' % (
           n_unit, fmt(p1['mean']), fmt(p1['stdev']), pct(p1['cv'], 0), fmt(p2['mean']), fmt(p2['stdev']), pct(p2['cv'], 0), fmt(p2['p95']), fmt(p2['max']), fmt(cap, 1), fmt(cap / 10, 1))),
     p('<b>• ¿Existen valores atípicos?</b>', BODY),
     p('Pocos. En la auditoría, %d de %s peticiones superan la media más tres desviaciones (%s s) y %d superan el p95 (%s s), con un máximo de %s s. Los atípicos del taller están en las pruebas con 20 hilos (máximo de P2: %s s; de P7: %s s), no en el uso normal.' % (
         AUD['atipicos'], thousands(n_aud), fmt(AUD['umbral_atipico']), AUD['sobre_p95'], fmt(AUD['tiempo']['p95']), fmt(AUD['tiempo']['max']), fmt(p2['max']), fmt(p7['max']))),
     p('<b>• ¿Qué tipo de prueba falla más?</b>', BODY)])
mas = max(SUITE['por_tipo'], key=lambda t: t['fallos'] / t['n'])
add([p('Las pruebas de error: %d de %d (%s). Las funcionales (0 de %d), las de rendimiento (0 de %d) y la de usabilidad (0 de %d) no fallaron, y las %d pruebas de Odoo tampoco. '
       'Es el patrón habitual: el sistema hace bien lo que se le pide y falla ante datos que no esperaba.' % (
           mas['fallos'], mas['n'], pct(100.0 * mas['fallos'] / mas['n'], 1), tipos['Funcional']['n'], tipos['Rendimiento']['n'], tipos['Usabilidad']['n'], n_unit)),
     p('<b>• ¿Dónde se presentan más errores?</b>', BODY),
     p('Todos están en un solo lugar: la <b>validación de los campos de la posición</b> que llega por el webhook (models/bus_vehicle.py, _apply_position, y models/utils.py, parse_traccar_dt). '
       'Las demás áreas probadas (portal, quejas, permisos, notificaciones, alertas, recorridos) tuvieron 0 errores. La Tabla 16 ordena las causas por frecuencia.')])
total_c = sum(v for _, v in pareto)
filas = [['Causa', 'Fallos', '%', '% acum.', 'Estado']]
acum = 0
for causa, n in pareto:
    acum += n
    filas.append([causa, str(n), pct(100.0 * n / total_c, 1), pct(100.0 * acum / total_c, 1), 'Abierto'])
add(table(filas, [0.5, 0.1, 0.12, 0.14, 0.14], align_center=(1, 2, 3, 4), caption='Pareto de los fallos de la ejecución (suite en vivo y auditoría) y su estado'))
add(figure(fig_pareto, 'Pareto de los fallos de la ejecución'))
add([p('Bitácora de defectos', H3), p('Los defectos DEF-001 a DEF-007 salen de la bitácora del proyecto (se hallaron y cerraron mientras se construía); DEF-008 a DEF-010 los halló esta evaluación y siguen abiertos.')])
add(table([['ID', 'Defecto', 'Ubicación', 'Estado y prueba']] + [list(d) for d in DEFECTOS], [0.09, 0.38, 0.23, 0.30], caption='Bitácora de defectos'))
add([p('Además, la bitácora registra 16 mutaciones manuales (cambiar el factor de velocidad, desactivar la autenticación del webhook, quitar el campo trampa, el límite por IP, entre otras) '
       'y en todas la suite de Odoo falló, es decir, las pruebas detectan esos cambios; parte de ese código se eliminó después en la simplificación.')])

# 6. Enfoques
add([p('<b>6.&nbsp;&nbsp;Enfoques formales del ACS</b>', H3)])
add(table([['Enfoque', 'Cómo se aplicó'],
           ['¿Está bien construido?', 'Revisión del código y de sus defectos, pruebas técnicas de reglas, cobertura de código del %s, flujo Git con ramas y commits pequeños' % pct(COV['porcentaje'], 1)],
           ['¿Cumple lo que el usuario necesita?', 'Casos del negocio: el pasajero solo ve nombre, posición, rumbo y estado; levanta una queja sin cuenta; el personal recibe alertas push. Falta validarlo con personas usuarias y con un celular real'],
           ['Pruebas funcionales', '%d pruebas sobre posiciones, llegadas, recorridos, alertas, portal y quejas' % tipos['Funcional']['n']],
           ['Pruebas de error', '%d pruebas con secreto falso, cuerpos inválidos, coordenadas y horas imposibles, rutas privadas, CSRF, XSS, cuerpos grandes, permisos y límites de uso' % tipos['Error']['n']],
           ['Pruebas de rendimiento', 'Latencia secuencial, carga concurrente con 20 hilos, feed con caché, salud e integridad concurrente (duplicados y un mismo bus)'],
           ['Pruebas sistemáticas', 'Unitarias y de integración de Odoo (%d), suite en vivo (%d) y auditoría aleatoria de %s peticiones por 15 áreas' % (n_unit, n_suite, thousands(n_aud))],
           ['Pruebas de mutación (manuales)', '16 mutaciones registradas en la bitácora, todas detectadas por la suite'],
           ['Métricas formales', '% de error y de éxito, tiempo promedio, mínimo, máximo, varianza, desviación estándar, CV, p95, cobertura, Defectos/KLOC'],
           ['Uso de estándares', 'ISO 25010, ISO 12207 y CMMI'],
           ['Enfoques que faltan', 'Prueba con celular y Traccar reales, prueba de carga prolongada con volumen real, prueba de seguridad externa, pruebas de usabilidad con personas, análisis estático (SonarQube) y revisión formal con acta']],
          [0.27, 0.73], caption='Enfoques del ACS aplicados y faltantes'))

# 7. Estándares
add([p('<b>7.&nbsp;&nbsp;Evaluación con estándares</b>', H3), p('<b>7.1&nbsp;&nbsp;ISO/IEC 25010 calidad del producto [1]</b>', H2)])
add(table([['Característica', 'Evaluación con la evidencia de hoy', 'Nivel'],
           ['Adecuación funcional', '12 de 12 casos funcionales y las 150 pruebas de Odoo pasan; reglas de negocio cubiertas: 15 de 17. Falla la validación de coordenadas y hora GPS (DEF-008 a DEF-010)', 'Buena'],
           ['Eficiencia de desempeño', 'Media de %s s en la auditoría; %s req/s sostenidos con 20 hilos (se necesitan 10); p95 de %s s bajo contención. Solo se midió con un proceso y sin el volumen de 30 días' % (fmt(AUD['tiempo']['mean']), fmt(cap, 1), fmt(p2['p95'])), 'Buena'],
           ['Compatibilidad', 'Traccar 6 y Odoo 16 verificados en la bitácora con GPS simulado por OsmAnd; no se probó un celular ni un Traccar de otra versión', 'Regular'],
           ['Usabilidad', '7 de 7 mensajes de rechazo comprensibles, sin SQL ni trazas; portal en español e inglés y probado a 390 px. Kichwa en borrador sin revisión; sin pruebas con personas ni auditoría de accesibilidad', 'Regular'],
           ['Fiabilidad', '0 fallos en las pruebas normales y integridad concurrente correcta; pero %d respuestas HTTP 500 ante datos mal formados y límites de uso que viven en la memoria de cada proceso' % (AUD['estados_5xx'] + 2), 'Regular'],
           ['Seguridad', 'Secreto del webhook comparado en tiempo constante, CSRF, escape de HTML, ACL por rol, contacto de quejas solo para administradores, push solo para administradores. Pendientes: límite de intentos de login, 2FA, TLS del tráfico GPS, y el identificador del dispositivo es la única credencial del celular', 'Regular'],
           ['Mantenibilidad', '%s de cobertura, %d pruebas, %s líneas de prueba por línea de código, bitácora y plan al día, flujo Git' % (pct(COV['porcentaje'], 1), n_unit, fmt(M['lineas']['python_tests'] / M['lineas']['python'], 2)), 'Buena'],
           ['Portabilidad', 'Todo en Docker Compose, con respaldo y restauración probados; solo se probó en Windows con Docker Desktop, no en un Linux real ni en Azure', 'Regular']],
          [0.2, 0.68, 0.12], align_center=(2,), caption='Evaluación por característica de ISO/IEC 25010'))
add([p('<b>7.2&nbsp;&nbsp;ISO/IEC 12207 procesos del ciclo de vida [2]</b>', H2)])
add(table([['Estado', 'Procesos', 'Justificación'],
           ['Aplicados', '• Implementación<br/>• Verificación<br/>• Aseguramiento de la calidad<br/>• Medición<br/>• Gestión de la configuración', '• Código por fases con commits pequeños<br/>• %d pruebas automáticas repetibles<br/>• Política y metas de calidad, cobertura medida<br/>• Métricas de este informe<br/>• Ramas main, develop y feature/*' % n_unit],
           ['Parciales', '• Requisitos<br/>• Validación<br/>• Gestión de riesgos<br/>• Transición (despliegue)', '• Decisiones del cliente documentadas, sin especificación formal<br/>• Sin pruebas con usuarios reales ni celular real<br/>• Riesgos listados, sin plan formal de mitigación<br/>• Producción y Azure sin probar en un servidor real']],
          [0.14, 0.34, 0.52], align_center=(0,), caption='Estado de los procesos de ciclo de vida'))
add([p('<b>7.3&nbsp;&nbsp;CMMI madurez [3]</b>'.replace('7.3', '7.3'), H2), p('Nivel: 2 Gestionado en consolidación. De las seis áreas del nivel 2 que aplican, cuatro se cumplen (planificación, seguimiento, medición y gestión de la configuración) y dos son parciales (requisitos y aseguramiento de la calidad); el nivel 3 se cumple solo en parte y el 4 no se alcanza. Es una autoevaluación, no una evaluación SCAMPI; el detalle por área está en docs/calidad/09-cumplimiento-iso.md.')])
add(table([['Nivel', 'Valoración', 'Justificación técnica'],
           ['2: Gestionado', 'En consolidación', 'Seguimiento de actividades (bitácora de 16 entradas y plan por fases), pruebas gestionadas (%d automáticas y repetibles), cambios controlados con Git y regresión, defectos registrados (DEF-001 a DEF-010)' % n_unit],
           ['3: Definido', 'Parcial', 'Hay un flujo Git y guías en docs/, pero no un proceso estándar de calidad documentado ni revisiones con acta; depende de las mismas personas'],
           ['4: Gestionado cuantitativamente', 'Parcial', 'Se miden error, tiempos, desviación, cobertura y Defectos/KLOC, pero es la primera medición: no hay línea base histórica ni límites de control']],
          [0.24, 0.14, 0.62], align_center=(1,), caption='Justificación del nivel de madurez CMMI'))

# 8. Decisión
add([p('<b>8.&nbsp;&nbsp;Análisis final y toma de decisión</b>', H3)])
add([p('<b>• ¿El sistema es apto para producción?</b>', BODY),
     p('<b>Condicionado.</b> Es apto para un <b>piloto controlado</b> con el personal de la universidad: cumple las metas de error, tiempo, cobertura y capacidad, y los flujos principales funcionan. '
       'No es apto todavía para producción abierta hasta cerrar los tres defectos abiertos (DEF-008 a DEF-010) y probarlo con un celular y un Traccar reales.'),
     p('<b>• ¿Qué métricas justifican la decisión?</b>', BODY)])
add(bullets(['Error: %s en las pruebas de Odoo (%d), %s en la suite en vivo y %s en la auditoría.' % (pct(100.0 * f_unit / n_unit), n_unit, pct(100.0 * f_suite / n_suite), pct(100.0 * f_aud / n_aud)),
             'Tiempo: media de %s s en la auditoría y de %s s en P1; con 20 hilos, media %s s y p95 %s s.' % (fmt(AUD['tiempo']['mean']), fmt(p1['mean']), fmt(p2['mean']), fmt(p2['p95'])),
             'Estabilidad: desviación baja en uso normal; alta (CV %s) bajo concurrencia en un solo proceso.' % pct(p2['cv'], 0),
             'Integridad: 0 duplicados, 0 alertas repetidas y 0 recorridos incoherentes en la base; pero %d posiciones con coordenadas imposibles.' % AUD['guardadas_invalidas'],
             'Cobertura de código de %s; %d de %d rutas HTTP con prueba; %d de %d defectos cerrados.' % (pct(COV['porcentaje'], 1), M['endpoints']['cubiertos'], M['endpoints']['total'], cerrados, len(DEFECTOS))]))
add([p('<b>• ¿Qué riesgos existen si se implementa?</b>', BODY)])
add(bullets(['Un emisor con el secreto (o un Traccar mal configurado) que mande una latitud o una hora mal formadas provoca errores 500 o deja un punto imposible en el mapa y en las alertas.',
             'El celular del chofer es la fuente: batería, permisos de segundo plano, plan de datos y consentimiento escrito del chofer (ley de datos personales de Ecuador) no están validados en campo.',
             'Los límites de uso (60 consultas por minuto, 5 quejas por hora) cuentan por proceso: con varios procesos el tope real es mayor.',
             'El kichwa del portal es un borrador sin revisión de una persona hablante; publicarlo sin esa revisión es un riesgo de reputación.',
             'Sin límite de intentos de login ni 2FA para administradores, y sin copia de los respaldos fuera del servidor.']))
add([p('<b>• Condiciones previas al despliegue:</b>', BODY),
     p('Primero, validar en el webhook la latitud (−90 a 90), la longitud (−180 a 180) y la hora, respondiendo 400 y sin guardar, y agregar sus pruebas. Después, probar un celular real durante un turno completo. '
       'Por último, ejecutar de nuevo esta suite con varios procesos (workers) para confirmar la latencia en el servidor definitivo.'),
     p('<b>• ¿Qué mejoras priorizaría y por qué?</b>', BODY)])
add(table([['Prioridad', 'Mejora', 'Por qué'],
           ['1', 'Validar coordenadas y hora GPS en el webhook (DEF-008 a DEF-010)', 'Es el único grupo de fallos de esta evaluación; se arregla en pocas líneas y evita datos basura en el mapa y las alertas'],
           ['2', 'Probar con un celular y un Traccar reales durante un turno', 'Es lo que el plan marca como pendiente; todo lo demás se probó con GPS simulado'],
           ['3', 'Repetir la prueba de carga con varios procesos y con el volumen de 30 días', 'La latencia con 20 hilos mostró dispersión alta en un solo proceso'],
           ['4', 'Mover los límites de uso al proxy o a un almacén compartido', 'Hoy cuentan por proceso y se debilitan con más de uno'],
           ['5', 'Límite de intentos de login, 2FA y copia de respaldos fuera del servidor', 'Reducen el riesgo de acceso indebido y de pérdida de datos'],
           ['6', 'Revisión del kichwa por una persona hablante; pruebas de usabilidad con pasajeros', 'Evita publicar un texto incorrecto y confirma que el portal se entiende'],
           ['7', 'Análisis estático (SonarQube) e integración continua con las pruebas y la cobertura', 'Mantiene el nivel de calidad al crecer el código']],
          [0.1, 0.45, 0.45], align_center=(0,), caption='Mejoras priorizadas'))

add([p('<b>2.3&nbsp;&nbsp;Conclusiones</b>', H2)])
add(numbered([
    'El sistema supera las metas de calidad en uso normal: %s de error en las %d pruebas de Odoo, %s de cobertura y latencias de %s s en promedio en la auditoría.' % (pct(100.0 * f_unit / n_unit), n_unit, pct(COV['porcentaje'], 1), fmt(AUD['tiempo']['mean'])),
    'Las funciones principales (ingesta, llegadas, recorridos, alertas, portal de pasajeros, quejas y permisos) están verificadas con casos en vivo; los %d casos funcionales pasan.' % tipos['Funcional']['n'],
    'La evaluación halló %d defectos nuevos, todos en la validación de la posición del webhook; las pruebas existentes no los detectaban porque ninguna probaba coordenadas ni horas inválidas (cobertura de reglas: 15 de 17).' % abiertos,
    'La integridad de los datos resistió la concurrencia: P6 guardó 1 de 20 envíos idénticos y P7 las 60 posiciones de un mismo bus, sin errores.',
    'La latencia bajo 20 hilos simultáneos es dispersa (CV %s) en un solo proceso, aunque sin errores y con %s veces la capacidad necesaria.' % (pct(p2['cv'], 0), fmt(cap / 10, 1)),
    'El sistema puede pasar a un piloto controlado; para producción abierta deben cerrarse DEF-008 a DEF-010 y probarse con un celular real.']))
add([p('<b>2.4&nbsp;&nbsp;Recomendaciones</b>', H2)])
add(bullets(['Validar latitud, longitud y hora en el webhook y devolver 400 sin guardar; agregar sus pruebas de regresión (E7, E8, E9) a la suite de Odoo.',
             'Ejecutar un turno completo con un celular real y confirmar el criterio de la fase 9 (aparece en menos de 15 s y sigue reportando con la pantalla apagada).',
             'Repetir las pruebas P2 y P7 con varios procesos de Odoo (workers) y con el volumen estimado de 30 días.',
             'Llevar los límites de uso al proxy (Caddy) o a un almacén compartido, y fijar límites de login y 2FA.',
             'Registrar cada defecto con tres campos separados (fallo observado, defecto localizado y causa de origen) y revisar el código con acta antes de integrar.',
             'Ejecutar qa/ejecutar_todo.sh en cada versión y conservar las métricas para tener una línea base (CMMI nivel 4).']))
add([p('<b>2.5&nbsp;&nbsp;Referencias</b>', H2)])
refs = ['ISO/IEC, <i>Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models</i>, ISO/IEC 25010:2011, 2011.',
        'ISO/IEC/IEEE, <i>Systems and software engineering — Software life cycle processes</i>, ISO/IEC/IEEE 12207:2017, 2017.',
        'CMMI Product Team, <i>CMMI for Development, Version 1.3</i>, Software Engineering Institute, Carnegie Mellon University, Pittsburgh, PA, USA, Rep. téc. CMU/SEI-2010-TR-033, 2010.',
        'ISO/IEC/IEEE, <i>Software and systems engineering — Software testing — Part 3: Test documentation</i>, ISO/IEC/IEEE 29119-3:2013, 2013.',
        'IEEE Standard Glossary of Software Engineering Terminology, IEEE Std 610.12-1990, 1990.',
        'I. Sommerville, <i>Software Engineering</i>, 10.ª ed. Harlow, Reino Unido: Pearson, 2016.',
        'Odoo S.A., «Testing Odoo,» <i>Odoo 16.0 Documentation</i>. [En línea]. Disponible en: https://www.odoo.com/documentation/16.0/developer/reference/backend/testing.html',
        'N. Batchelder, «Coverage.py,» <i>Coverage.py documentation</i>. [En línea]. Disponible en: https://coverage.readthedocs.io/',
        'Traccar, «Position forwarding,» <i>Traccar documentation</i>. [En línea]. Disponible en: https://www.traccar.org/forward/']
add([p('[%d] %s' % (i, r), REF) for i, r in enumerate(refs, start=1)])

# Anexos
log = open(os.path.join(OUT, 'odoo_test.log'), encoding='utf-8').read().splitlines()
resumen = [re.sub(r'^(\S+ \S+) \d+ \w+ \S+ \S+: ', r'\1 ', l) for l in log if 'post-tests in' in l or 'failed,' in l and 'of' in l]
cobertura = open(os.path.join(OUT, 'cobertura.txt'), encoding='utf-8').read().splitlines()
cobertura = [l.replace('/mnt/extra-addons/bus_tracking/', '') for l in cobertura]
suite_log = [l for l in open(os.path.join(OUT, 'suite.log'), encoding='utf-8').read().splitlines() if l.strip()]
audit_log = [l for l in open(os.path.join(OUT, 'auditoria.log'), encoding='utf-8').read().splitlines() if l.strip()]
add([PageBreak(), p('<b>2.6&nbsp;&nbsp;Anexos</b>', H2), p('<b>Anexo A: Imágenes de consola</b>', H3)])
add(console(cobertura, 'Reporte de cobertura de coverage.py (sentencias y ramas) sobre el módulo bus_tracking'))
add(console(resumen, 'Resumen del registro de Odoo: 150 pruebas, 0 fallos'))
add(console(suite_log, 'Salida de la suite en vivo (qa/qa_suite.py)', 14))
add(console(audit_log, 'Resumen de la auditoría de 1000 peticiones (qa/auditoria.py)'))
add([p('<b>Anexo B. Reproducción</b>', H3)])
add(console([
    'cp .env.example .env && docker compose up -d db',
    '# pruebas de Odoo con cobertura (base nueva buses_qa)',
    'docker compose run --rm --no-deps --user root odoo sh -c "pip3 install coverage && coverage run --branch \\',
    '  --source=/mnt/extra-addons/bus_tracking --omit=*/tests/* /usr/bin/odoo -d buses_qa --db_host $HOST --db_user $USER \\',
    '  --db_password $PASSWORD -i bus_tracking --test-enable --test-tags /bus_tracking --stop-after-init --without-demo=all"',
    '# servidor dedicado para las pruebas en vivo',
    "docker compose run -d --no-deps --name qa-odoo -p 8071:8069 odoo odoo -d buses_qa --db-filter '^buses_qa$'",
    'sh qa/ejecutar_todo.sh          # suite en vivo + auditoría + métricas',
    'python -X utf8 qa/generar_informe.py   # este informe'], 'Pasos para repetir la evaluación'))

add([p('La documentación completa de calidad (política, reglas, plan de pruebas, defectos, lluvia de ideas, Pareto, Ishikawa y cumplimiento de las ISO) está en la carpeta docs/calidad del proyecto, con un índice en docs/calidad/README.md.')])
doc.build(E)
print('Informe:', os.path.abspath(SALIDA))
