"""Escribe el documento de las 12 métricas (docs/calidad/14-metricas-de-transporte.md) desde el propio código.

No se ejecuta con Python: se pasa a `odoo shell` del Odoo de DESARROLLO (con los 12 recorridos simulados de
scripts/seed_recorridos.py). Las fórmulas, las fuentes, los umbrales y las consultas SQL salen de
`models/bus_kpi.py` y los resultados salen de calcularlos ahora, así que el documento no puede quedar desfasado.

    docker compose exec -T odoo odoo shell -d buses --no-http --db_host db --db_user odoo --db_password odoo \\
        --log-level=error < scripts/doc_metricas.py > salida.txt

Imprime el documento entre las marcas <<<DOC y DOC>>>.
"""
from datetime import date

from odoo.addons.bus_tracking.models.bus_kpi import SQL, THRESHOLDS

STATUS_ES = {'good': 'en la meta', 'warn': 'atención', 'bad': 'fuera de la meta', 'info': 'cifra sin umbral',
             'na': 'sin datos'}
GROUP_ES = {'transport': 'Servicio de transporte', 'software': 'Calidad del software'}
# which thresholds are read on the absolute value (a difference with the plan)
ABSOLUTE = {'T6', 'T7'}


def number(value):
    if value is None:
        return '—'
    if isinstance(value, float) and value == int(value):
        value = int(value)
    return ('%s' % value).replace('.', ',')


def thresholds(code, unit):
    if code not in THRESHOLDS:
        return 'Sin umbral: es un conteo; se compara entre líneas y entre periodos.'
    good, ok, higher = (number(THRESHOLDS[code][0]), number(THRESHOLDS[code][1]), THRESHOLDS[code][2])
    sign = ' (se juzga sobre el valor absoluto de la diferencia)' if code in ABSOLUTE else ''
    if higher:
        return 'Verde desde %s %s, ámbar desde %s %s, rojo por debajo%s.' % (good, unit, ok, unit, sign)
    return 'Verde hasta %s %s, ámbar hasta %s %s, rojo por encima%s.' % (good, unit, ok, unit, sign)


env = env(context=dict(env.context, lang='es_EC'))          # noqa: F821 (provided by `odoo shell`)
kpi = env['bus.kpi']
result = kpi.compute(scope='simulated')
metrics = result['metrics']
real = kpi.compute(scope='all')
status_all = {m['code']: m for m in real['metrics']}
sim_trips = env['bus.trip'].search_count([('simulated', '=', True), ('state', 'in', ('done', 'incomplete'))])

out = []
w = out.append
w('# Métricas de transporte y de software')
w('')
w('Evidencia de la Actividad 7 del proyecto final (criterio 6, métricas y tablero): **8 métricas de transporte y 4 de calidad del software**, cada una con su fórmula, su fuente de datos, su unidad,')
w('su resultado, su estado y su interpretación. Este documento **se genera desde el código** (`scripts/doc_metricas.py` lee `models/bus_kpi.py` y calcula cada cifra al momento): no hay ningún valor escrito a mano.')
w('')
w('Las mismas cifras se ven en el menú **Buses › Indicators › Odoo dashboard** (pestaña «Formulas», con la consulta de cada una) y en **Grafana** (`docs/calidad/15-tablero-grafana.md`);')
w('las pruebas comprueban que los dos tableros dan las mismas cifras que estas consultas (`TestSameFiguresAsTheIndicators`).')
w('')
w('## 1. Cómo se calculan')
w('')
w('- **Nada es estático.** Cada indicador es una consulta SQL sobre los registros guardados. Al entrar un recorrido, una llegada, una alerta o una posición, la cifra cambia en la siguiente consulta.')
w('- **Periodo.** Por defecto, los últimos 30 días (fecha local de Ecuador). El tablero permite 7, 30 o 90 días o fechas elegidas, una o varias líneas, y datos reales, simulados o ambos.')
w('- **Recorridos que cuentan.** Solo los recorridos **cerrados** (hechos o incompletos). Un recorrido que aún corre no entra hasta que termina.')
w('- **Datos simulados.** Los recorridos simulados llevan `simulated = True` y su escenario; nunca se mezclan en silencio con los reales (filtro «Real / Simulated / Both»).')
w('- **Tolerancias** (Ajustes › Trips and punctuality): puntualidad 5 min; ventana del recorrido 30 min; salida tarde 10 min; duración marcada a partir de 25 %. Cambiarlas cambia las cifras.')
w('- **Parámetros de las consultas:** `%(d1)s` y `%(d2)s` son el primer y el último día del periodo; `%(routes)s` es la lista de líneas (vacía = todas); `%(scope)s` es `all`, `real` o `simulated`.')
w('')
w('## 2. Resumen de la corrida')
w('')
w('Corrida del %s en la base de **desarrollo**, con datos **simulados** (%d recorridos cerrados, identificados como simulados; ver `docs/calidad/13-recorridos-de-prueba.md`), periodo %s a %s.'
  % (date.today().isoformat(), sim_trips, result['period']['from'], result['period']['to']))
w('')
w('| Código | Indicador | Unidad | Resultado | Estado | Umbrales |')
w('|---|---|---|---|---|---|')
for m in metrics:
    w('| %s | %s | %s | **%s** | %s | %s |' % (m['code'], m['name'], m['unit'], number(m['value']), STATUS_ES[m['status']],
                                                  thresholds(m['code'], m['unit'])))
w('')
w('Los indicadores S1 y S2 miden el sistema con Traccar real: en desarrollo no hay auditoría de sincronización (S2 «sin datos») ni posiciones rechazadas. En producción se calculan con los registros reales.')
w('')
w('## 3. Cada indicador')
for group in ('transport', 'software'):
    w('')
    w('### %s' % GROUP_ES[group])
    for m in [m for m in metrics if m['group'] == group]:
        w('')
        w('#### %s · %s' % (m['code'], m['name']))
        w('')
        w('| | |')
        w('|---|---|')
        w('| **Qué mide** | %s |' % m['interpretation'])
        w('| **Fórmula** | %s |' % m['formula'])
        w('| **Fuente de datos** | `%s` |' % m['source'].replace('`', ''))
        w('| **Unidad** | %s |' % m['unit'])
        w('| **Umbrales** | %s |' % thresholds(m['code'], m['unit']))
        w('| **Resultado de esta corrida** | **%s %s**, %s: %s |' % (number(m['value']), m['unit'] if m['value'] is not None else '',
                                                                   STATUS_ES[m['status']], m['detail']))
        w('')
        w('Consulta que la reproduce (la misma que ejecuta el tablero):')
        w('')
        w('```sql')
        w(m['sql'])
        w('```')
w('')
w('## 4. Cómo comprobar una cifra por su cuenta')
w('')
w('1. En Odoo, **Buses › Indicators › Odoo dashboard › Formulas** muestra, para cada indicador, la fórmula, la fuente y la consulta.')
w('2. En la base: ejecutar la consulta con los parámetros del periodo, por ejemplo en `psql`:')
w('')
example = (SQL['T1'].strip().replace('%(d1)s', "'%s'" % result['period']['from'])
           .replace('%(d2)s', "'%s'" % result['period']['to']).replace('%(routes)s', 'NULL').replace('%(scope)s', "'all'"))
w('```sql')
w('-- T1 del periodo de esta corrida, todas las líneas, datos reales y simulados: devuelve (recorridos hechos, recorridos cerrados)')
w(example)
w('```')
w('')
w('3. En Grafana, cada panel de «Resumen» tiene su consulta en el menú del panel › Inspect › Query, sobre las vistas `kpi_*` (`docs/guias/GRAFANA.md`).')
w('4. Las pruebas automáticas (`tests/test_kpi.py`, `tests/test_dashboard.py`, `tests/test_grafana_dashboards.py`) construyen recorridos a mano con resultado conocido y comprueban cada fórmula.')
w('')
w('## 5. Lectura de los resultados')
w('')
w('Con los 12 recorridos simulados (cada uno con una situación distinta, `13-recorridos-de-prueba.md`) los indicadores se mueven como se espera de la situación: **los recorridos incompletos bajan el cumplimiento de ruta (T1) y las paradas atendidas (T4)**;')
w('**los retrasos suben el retraso promedio (T3) y bajan la puntualidad (T2)**; **los desvíos suben la desviación media (T5) y la diferencia de distancia (T6)**; y la detección correcta (S4) compara lo que cada escenario debía provocar con lo que las reglas detectaron.')
w('Con datos reales la lectura es la misma, pero las cifras serán las de la operación; lo que importa es la tendencia entre periodos y entre líneas, que el tablero muestra junto a cada indicador.')
print('<<<DOC')
print('\n'.join(out))
print('DOC>>>')
