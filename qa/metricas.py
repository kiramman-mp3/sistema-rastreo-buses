"""Quality metrics of bus_tracking from the evidence files, in the same spirit as the course's metrics script.

    python -X utf8 qa/metricas.py

Reads (in docs/calidad/evidencias): suite.json, auditoria.json, odoo_test.log, coverage.json.
Asks the QA database (container sistema-rastreo-buses-db-1) about the state of the data.
Writes metricas.json.
"""
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime

from common import OUT, describe, load_json, save_json

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
ADDON = os.path.join(ROOT, 'addons', 'bus_tracking')
DB_CONTAINER = 'sistema-rastreo-buses-db-1'


# -- unit suite (Odoo tests) -----------------------------------------------------------------
def parse_unit_log(path):
    """Per-test duration = time until the next 'Starting' line (the log has no per-test timer)."""
    starts = []
    pattern = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3}) .*bus_tracking\.tests\.(\w+): Starting (\w+)\.(\w+)')
    end = None
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            m = pattern.match(line)
            if m:
                starts.append((datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S,%f'), m.group(2), m.group(3), m.group(4)))
            elif 'post-tests in' in line:
                end = datetime.strptime(line[:23], '%Y-%m-%d %H:%M:%S,%f')
            m2 = re.search(r'(\d+) failed, (\d+) error\(s\) of (\d+) tests', line)
            if m2:
                failed, errors, total = map(int, m2.groups())
    tests = []
    for i, (when, module, cls, name) in enumerate(starts):
        nxt = starts[i + 1][0] if i + 1 < len(starts) else end
        tests.append({'archivo': module, 'clase': cls, 'prueba': name, 'tiempo': (nxt - when).total_seconds() if nxt else 0.0})
    return tests, {'fallos': failed, 'errores': errors, 'total': total}


def lines_of_code():
    """Non-blank, non-comment lines of the module (tests excluded), the base for Defects/KLOC."""
    def count(paths, comment_prefixes):
        total = 0
        for path in paths:
            with open(path, encoding='utf-8') as handle:
                for line in handle:
                    text = line.strip()
                    if text and not text.startswith(comment_prefixes):
                        total += 1
        return total

    def files(extensions, skip=()):
        for folder, dirs, names in os.walk(ADDON):
            dirs[:] = [d for d in dirs if d not in ('tests', 'lib', 'fonts', 'img', '__pycache__') and d not in skip]
            for name in names:
                if name.endswith(extensions):
                    yield os.path.join(folder, name)

    return {
        'python': count(files(('.py',)), ('#',)),
        'python_tests': count([os.path.join(ADDON, 'tests', n) for n in os.listdir(os.path.join(ADDON, 'tests')) if n.endswith('.py')], ('#',)),
        'xml': count(files(('.xml',)), ('<!--',)),
        'js': count(files(('.js',)), ('//', '*', '/*')),
        'css': count(files(('.css', '.scss')), ('/*', '*')),
    }


def endpoint_coverage():
    """A route counts as covered when some unit or live test sends a request to its path."""
    routes = []
    for name in sorted(os.listdir(os.path.join(ADDON, 'controllers'))):
        if name.endswith('.py'):
            with open(os.path.join(ADDON, 'controllers', name), encoding='utf-8') as handle:
                routes += [(name, m.group(1)) for m in re.finditer(r"@http\.route\('([^']+)'", handle.read())]
    corpus = ''
    for folder in (os.path.join(ADDON, 'tests'), os.path.join(ROOT, 'qa')):
        for name in os.listdir(folder):
            if name.endswith('.py'):
                with open(os.path.join(folder, name), encoding='utf-8') as handle:
                    corpus += handle.read()
    corpus += "WEBHOOK = '/bus_tracking/traccar/webhook'"
    result = []
    for controller, path in routes:
        needle = re.sub(r'<[^>]+>', '', path).rstrip('/')
        hit = needle in corpus or (needle.endswith('/buses.json') and 'buses.json' in corpus)
        if path.startswith('/rutas/<'):
            hit = '/rutas/' in corpus
        result.append({'controlador': controller, 'ruta': path, 'cubierta': bool(hit)})
    return result


def psql(sql):
    out = subprocess.run(['docker', 'exec', DB_CONTAINER, 'psql', '-U', 'odoo', '-d', 'buses_qa', '-At', '-c', sql],
                         capture_output=True, text=True, encoding='utf-8')
    return out.stdout.strip()


def data_state():
    checks = OrderedDict([
        ('Posiciones guardadas (total)', "SELECT count(*) FROM bus_position"),
        ('Posiciones con latitud o longitud fuera de rango', "SELECT count(*) FROM bus_position WHERE latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180"),
        ('Posiciones con velocidad negativa', "SELECT count(*) FROM bus_position WHERE speed < 0"),
        ('Pares (bus, hora GPS) duplicados', "SELECT count(*) FROM (SELECT vehicle_id, fix_time FROM bus_position GROUP BY 1,2 HAVING count(*)>1) d"),
        ('Buses con más de una alerta abierta del mismo tipo', "SELECT count(*) FROM (SELECT vehicle_id, kind FROM bus_alert WHERE state='open' GROUP BY 1,2 HAVING count(*)>1) d"),
        ('Alertas cerradas sin hora de cierre', "SELECT count(*) FROM bus_alert WHERE state='closed' AND end_time IS NULL"),
        ('Recorridos con llegada anterior a la salida', "SELECT count(*) FROM bus_run WHERE arrival < departure"),
        ('Recorridos terminados sin llegada', "SELECT count(*) FROM bus_run WHERE state='done' AND arrival IS NULL"),
        ('Quejas con descripción fuera de 10 a 2000 caracteres', "SELECT count(*) FROM bus_complaint WHERE length(description) NOT BETWEEN 10 AND 2000"),
        ('Quejas sin folio asignado', "SELECT count(*) FROM bus_complaint WHERE name IS NULL OR name='/'"),
        ('Buses cuyo último estado no coincide con su posición más reciente',
         "SELECT count(*) FROM bus_vehicle v WHERE last_fix_time IS NOT NULL AND last_fix_time <> (SELECT max(fix_time) FROM bus_position p WHERE p.vehicle_id=v.id)"),
    ])
    return [{'consulta': label, 'valor': int(psql(sql) or 0)} for label, sql in checks.items()]


def main():
    suite = load_json('suite.json')
    audit = load_json('auditoria.json')
    coverage = json.load(open(os.path.join(OUT, 'coverage.json'), encoding='utf-8'))
    unit_tests, unit_summary = parse_unit_log(os.path.join(OUT, 'odoo_test.log'))

    by_file = OrderedDict()
    for t in unit_tests:
        by_file.setdefault(t['archivo'], []).append(t['tiempo'])
    unit_files = [{'archivo': k, 'n': len(v), **{a: b for a, b in describe(v).items() if a != 'n'}} for k, v in by_file.items()]

    cases = suite['casos']
    by_type = OrderedDict()
    for c in cases:
        by_type.setdefault(c['tipo'], []).append(c)
    types = []
    for kind, items in by_type.items():
        # performance cases carry the stats of their own requests; the others have one measured time each
        times = [c['tiempo'] for c in items if 'stats' not in c]
        means = [c['stats']['mean'] for c in items if 'stats' in c]
        sample = describe(times + means)
        types.append({'tipo': kind, 'n': len(items), 'fallos': sum(1 for c in items if c['estado'] != 'PASS'),
                      **{a: b for a, b in sample.items() if a != 'n'}})

    perf = [{'id': c['id'], 'objetivo': c['objetivo'], 'stats': c['stats'], 'errores': c.get('errores', 0), 'rps': c.get('rps')}
            for c in cases if 'stats' in c]
    covfiles = []
    for path, data in sorted(coverage['files'].items()):
        s = data['summary']
        covfiles.append({'archivo': path.split('bus_tracking/', 1)[1], 'sentencias': s['num_statements'], 'perdidas': s['missing_lines'],
                         'ramas': s['num_branches'], 'ramas_parciales': s['num_partial_branches'], 'cobertura': s['percent_covered']})
    totals = coverage['totals']

    endpoints = endpoint_coverage()
    kloc = lines_of_code()
    result = {
        'generado': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'unitarias': {**unit_summary, 'tiempos_por_archivo': unit_files, 'tiempo': describe([t['tiempo'] for t in unit_tests]),
                      'mas_lentas': sorted(unit_tests, key=lambda t: -t['tiempo'])[:5]},
        'suite': {'total': len(cases), 'fallos': sum(1 for c in cases if c['estado'] != 'PASS'), 'por_tipo': types, 'rendimiento': perf},
        'auditoria': {k: audit[k] for k in ('total', 'fallos', 'pct_error', 'tiempo', 'atipicos', 'umbral_atipico', 'sobre_p95',
                                            'estados_5xx', 'posiciones_nuevas', 'quejas_nuevas', 'fallos_por_causa', 'suplantacion_xff')},
        'cobertura': {'sentencias': totals['num_statements'], 'perdidas': totals['missing_lines'], 'ramas': totals['num_branches'],
                      'ramas_parciales': totals['num_partial_branches'], 'porcentaje': totals['percent_covered'],
                      'solo_lineas': 100.0 * (totals['num_statements'] - totals['missing_lines']) / totals['num_statements'],
                      'archivos': covfiles},
        'endpoints': {'total': len(endpoints), 'cubiertos': sum(1 for e in endpoints if e['cubierta']), 'detalle': endpoints},
        'lineas': kloc,
        'datos': data_state(),
    }
    save_json('metricas.json', result)
    print(json.dumps({k: result[k] for k in ('cobertura', 'endpoints', 'lineas', 'datos')}, ensure_ascii=False, indent=1)[:3500])
    return 0


if __name__ == '__main__':
    sys.exit(main())
