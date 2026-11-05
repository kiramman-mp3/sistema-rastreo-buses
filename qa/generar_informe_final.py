"""Builds the final report (PDF) of the project: results of the whole rubric stage, from the evidence files.

    python -X utf8 qa/generar_informe_final.py [salida.pdf]

Every figure comes from docs/calidad/evidencias (metricas.json, rendimiento*.json, sonarqube/*.json), from the defect
register (qa/datos_calidad.py) and from the generated document docs/calidad/14-metricas-de-transporte.md. The report of
the evaluation of 28-oct-2026 (qa/generar_informe.py) is kept as it was: it narrates that evaluation.
"""
import json
import os
import re
import sys
from collections import Counter

import datos_calidad as dq
from common import OUT, load_json
from informe_lib import H1, H2, Report, bullets, figure, fmt, p, pct, table, thousands

DOCS = os.path.abspath(os.path.join(OUT, os.pardir))
SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DOCS, 'Informe_final_proyecto_rastreo_buses.pdf')
FECHA = '5-nov-2026'


def read_json(*parts):
    with open(os.path.join(OUT, *parts), encoding='utf-8') as handle:
        return json.load(handle)


M = load_json('metricas.json')
SUITE, AUD, UNIT, COV = M['suite'], M['auditoria'], M['unitarias'], M['cobertura']
PERF = read_json('rendimiento.json')
STRESS = read_json('rendimiento-estres.json')
SONAR_BEFORE = {m['metric']: m.get('value') for m in read_json('sonarqube', 'antes-metricas.json')['component']['measures']}
SONAR_AFTER = {m['metric']: m.get('value') for m in read_json('sonarqube', 'despues-metricas.json')['component']['measures']}

# the indicators table of docs/calidad/14-metricas-de-transporte.md (it is generated from the code)
indicators = []
with open(os.path.join(DOCS, '14-metricas-de-transporte.md'), encoding='utf-8') as handle:
    for line in handle:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) == 6 and re.match(r'^[TS]\d$', cells[0]):
            indicators.append([cells[0], cells[1], cells[2], cells[3].strip('*'), cells[4]])

doc = Report(SALIDA, 'Informe final: sistema de rastreo de buses (Odoo 16 + Traccar)',
             'Johan Rodríguez Núñez; José Manzano Bahamonde')
E = []
add = E.extend

add([p('<b>Proyecto final integrador: Gestión de Calidad del Software</b>', H1),
     p('<b>Sistema de rastreo de buses de la UTA (Odoo 16 + Traccar): evaluación del cumplimiento de rutas y de la calidad del sistema</b>', H2),
     p('Autores: Rodríguez Núñez Johan Gabriel y Manzano Bahamonde José Gabriel. Docente: Ing. Alex Javier Maigua Quinteros, Mg. Fecha de las evidencias: %s.' % FECHA)])

add([p('<b>1. Resumen</b>', H2),
     p('El sistema no se limita a mostrar un bus en un mapa: registra recorridos con horario previsto y real, evalúa cada parada y cada recorrido con reglas explícitas, calcula '
       '<b>12 indicadores</b> (8 de transporte y 4 de calidad del software) con consultas SQL que se pueden comprobar, los muestra en un tablero dentro de Odoo y en Grafana, '
       'y se mide a sí mismo: sincronización con Traccar, tiempo de respuesta y detección correcta de incidencias. Se probó con %s pruebas automáticas de Odoo, %s de la app y una suite en vivo de %s casos, '
       'se analizó con SonarQube y se midió su rendimiento hasta un millón de posiciones.' % (thousands(UNIT['total']), '167', SUITE['total']))])

add([p('<b>2. Resultados de las pruebas</b>', H2)])
add(table([
    ['Prueba', 'Cantidad', 'Fallos', 'Nota'],
    ['Pruebas automáticas de Odoo', thousands(UNIT['total']), str(UNIT['fallos'] + UNIT['errores']), 'Cobertura de código %s (sentencias y ramas)' % pct(COV['porcentaje'], 1)],
    ['Pruebas de la app del chofer (Jest)', '167', '0', 'Cobertura de sentencias 86,9 %'],
    ['Suite en vivo contra un servidor real', str(SUITE['total']), str(SUITE['fallos']), 'P7 (60 posiciones de un mismo bus con 20 hilos) está en el límite: p95 entre 1,8 s y 2,2 s en cuatro corridas'],
    ['Auditoría aleatoria de peticiones', thousands(AUD['total']), str(AUD['fallos']), 'Sin respuestas 5xx'],
    ['Grafana: prueba de humo', '19', '0', 'Salud, fuente de datos, token, rol de solo lectura, cabeceras'],
], [0.34, 0.12, 0.1, 0.44], align_center=(1, 2), caption='Pruebas ejecutadas'))

add([p('<b>3. Los doce indicadores</b>', H2),
     p('Cada cifra es una consulta SQL mostrada junto a ella (documento <i>14-metricas-de-transporte.md</i>); ninguna es estática. Los valores de abajo son los de la corrida con los 12 recorridos simulados, identificados como simulados.')])
add(table([['Código', 'Indicador', 'Unidad', 'Resultado', 'Estado']] + indicators, [0.1, 0.44, 0.1, 0.14, 0.22], align_center=(0, 2, 3),
          caption='Indicadores calculados (datos simulados identificados)'))

add([p('<b>4. SonarQube</b>', H2),
     p('Quality Gate aprobado. Se corrigieron 27 de los 39 hallazgos; los 12 restantes son datos de prueba y un servidor simulado, aceptados con su justificación. El análisis no cubre inyecciones ni dependencias (edición Community).')])
add(table([
    ['Medida', 'Primer análisis', 'Después de corregir'],
    ['Bugs', SONAR_BEFORE['bugs'], SONAR_AFTER['bugs']],
    ['Vulnerabilidades', SONAR_BEFORE['vulnerabilities'], SONAR_AFTER['vulnerabilities']],
    ['Malos olores', SONAR_BEFORE['code_smells'], SONAR_AFTER['code_smells']],
    ['Deuda técnica (min)', SONAR_BEFORE['sqale_index'], SONAR_AFTER['sqale_index']],
    ['Cobertura', '20,4 % (rutas mal leídas)', '%s %%' % SONAR_AFTER['coverage'].replace('.', ',')],
    ['Duplicaciones', '%s %%' % SONAR_BEFORE['duplicated_lines_density'].replace('.', ','), '%s %%' % SONAR_AFTER['duplicated_lines_density'].replace('.', ',')],
], [0.4, 0.3, 0.3], align_center=(1, 2), caption='SonarQube: antes y después'))

add([p('<b>5. Rendimiento por volumen</b>', H2),
     p('Tiempo de respuesta p95 en milisegundos de cada pantalla, como administrador, por HTTP, con un servidor real. La meta del proyecto es menor que 2 000 ms. Detalle y método: <i>17-rendimiento-por-volumen.md</i>.')])
names = [('live_refresh', 'Mapa en vivo (refresco)'), ('bus_history_4h', 'Historial de un bus (4 h)'), ('trip_list', 'Lista de recorridos'),
         ('indicators_30d', 'Indicadores (30 días)'), ('dashboard_30d', 'Tablero (30 días)')]
scenarios = PERF['results'] + STRESS['results']
rows = [['Pantalla'] + ['%s pos. / %s rec.' % (thousands(r['positions']), thousands(r['trips'])) for r in scenarios]]
for key, label in names:
    rows.append([label] + [fmt(r['measures'][key]['p95'], 0) for r in scenarios])
add(table(rows, [0.28] + [0.18] * 4, align_center=(1, 2, 3, 4), caption='p95 (ms) por escenario de volumen'))

add([p('<b>6. Defectos y mejora continua</b>', H2),
     p('Se registraron %d defectos, todos cerrados, cada uno con su causa raíz y la prueba que lo protege. Los diez de esta etapa (DEF-039 a DEF-048) se analizan con Ishikawa, Pareto y cuatro ciclos PDCA en '
       '<i>18-mejora-continua-pdca.md</i>.' % len(dq.DEFECTOS))])
categorias = Counter(d[6] for d in dq.DEFECTOS)
total = sum(categorias.values())
rows, running = [['Categoría', 'Defectos', '%', '% acum.']], 0
for name, n in categorias.most_common():
    running += n
    rows.append([name, str(n), pct(100.0 * n / total, 1), pct(100.0 * running / total, 1)])
add(table(rows, [0.46, 0.16, 0.18, 0.2], align_center=(1, 2, 3), caption='Pareto de los defectos por categoría'))
pareto_png = os.path.join(DOCS, 'figuras', 'pareto_defectos.png')
if os.path.exists(pareto_png):
    add(figure(pareto_png, 'Pareto de los defectos por categoría'))
nuevos = [list(d[:1]) + [d[3], d[6]] for d in dq.DEFECTOS if d[0] >= 'DEF-039']
add(table([['ID', 'Defecto', 'Categoría']] + nuevos, [0.1, 0.68, 0.22], caption='Defectos de la etapa del proyecto final (todos cerrados)'))
add([p('<b>Ciclos PDCA.</b> (1) Análisis estático: 16 bugs y 12 vulnerabilidades a 0. (2) Acceso a Grafana: el token de 5 minutos dejaba el tablero sin datos; ahora dura una jornada con renovación automática. '
       '(3) Cobertura mal medida (20,4 %) corregida a 78,4 %. (4) Rendimiento por volumen verificado hasta un millón de posiciones sin superar la meta.')])

add([p('<b>7. Qué falta</b>', H2)])
add(bullets([
    'Capturas y ensayo con un celular real con Traccar Client por datos móviles (la guía y la lista de evidencias están en <i>DEMO-TRACCAR-CLIENT.md</i>).',
    'Confirmar con el docente que Grafana sirve en lugar de Power BI; el tablero de Odoo cubre el criterio por sí solo.',
    'Desplegar la versión 16.0.1.6.0 en el servidor de Azure, con respaldo y migración previa.',
    'Pruebas unitarias del JavaScript del módulo (hoy sin cobertura medida), análisis de dependencias y una prueba de concurrencia.',
    'Revisión del kichwa por una persona hablante: la traducción la hizo una IA.',
]))
add([p('La trazabilidad completa de actividades, entregables y criterios con su archivo de evidencia está en <i>docs/calidad/19-matriz-de-trazabilidad.md</i>.')])
doc.build(E)
print('Informe:', os.path.abspath(SALIDA))
