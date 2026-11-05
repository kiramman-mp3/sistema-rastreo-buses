"""Performance by volume: how the screens answer as the data grows.

    python -X utf8 qa/rendimiento_volumen.py                       # the three scenarios below
    python -X utf8 qa/rendimiento_volumen.py --scenarios 1000:100  # positions:trips, as many as wanted
    python -X utf8 qa/rendimiento_volumen.py --keep                # leave the database and the server for a look

It builds a throwaway database (buses_perf) with the development lines and buses, starts a real Odoo server in a
container, fills the tables with the volume of each scenario (qa/rendimiento_volumen.sql) and times, over HTTP and as an
administrator, what each screen asks for: the live map, the history of a bus, the list of trips, the indicators and the
dashboard. Each call is made REPEATS times after a warm-up; the result is the median (p50), the 95th percentile (p95)
and the size of the answer. The goal of the project is a p95 under 2 s (indicator S3).

The development stack must be up (docker compose up -d db). Writes docs/calidad/evidencias/rendimiento.json.
"""
import argparse
import http.cookiejar
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
DB = 'buses_perf'
PORT = 8071
BASE = 'http://localhost:%d' % PORT
SERVER = 'perf-odoo'
NETWORK = os.environ.get('COMPOSE_NETWORK', os.path.basename(ROOT) + '_default')
IMAGE = 'rastreo-odoo:16.0'
SCENARIOS = '1000:100,10000:1000,100000:5000'
REPEATS = 15
GOAL_MS = 2000.0
OUT = os.path.join(ROOT, 'docs', 'calidad', 'evidencias', 'rendimiento.json')
ODOO_ARGS = ['--db_host=db', '--db_user=odoo', '--db_password=odoo',
             '--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons']


def say(text):
    print('==> ' + text, flush=True)


def run(*args, stdin=None, check=True):
    env = dict(os.environ, MSYS_NO_PATHCONV='1')
    result = subprocess.run(args, cwd=ROOT, input=stdin, capture_output=True, text=True, encoding='utf-8',
                            errors='replace', env=env)
    if check and result.returncode:
        raise SystemExit('Failed: %s\n%s%s' % (' '.join(args), result.stdout[-1500:], result.stderr[-1500:]))
    return result


def psql(sql=None, database=DB, file_input=None, variables=()):
    args = ['docker', 'compose', 'exec', '-T', 'db', 'psql', '-U', 'odoo', '-d', database, '-v', 'ON_ERROR_STOP=1']
    for name, value in variables:
        args += ['-v', '%s=%s' % (name, value)]
    if sql is not None:
        return run(*args, '-tAc', sql).stdout.strip()
    return run(*args, '-f', '-', stdin=file_input).stdout


def odoo_container(*extra, detach=False, stdin=None):
    repo = ROOT
    base = ['docker', 'run', '--rm' if not detach else '-d', '--network', NETWORK]
    if detach:
        base += ['--name', SERVER, '-p', '%d:8069' % PORT]
    if stdin is not None:
        base += ['-i']
    base += ['-e', 'HOST=db', '-e', 'USER=odoo', '-e', 'PASSWORD=odoo',
             '-v', '%s/addons:/mnt/extra-addons:ro' % repo, '-v', '%s/scripts:/mnt/scripts:ro' % repo, IMAGE]
    return run(*base, *extra, stdin=stdin)


class Client:
    """A signed-in administrator talking JSON-RPC to the Odoo of the test."""

    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, path, params=None):
        body = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params or {}}).encode()
        request = urllib.request.Request(BASE + path, data=body, headers={'Content-Type': 'application/json'})
        with self.opener.open(request, timeout=300) as response:
            raw = response.read()
        answer = json.loads(raw)
        if 'error' in answer:
            raise SystemExit('%s failed: %s' % (path, answer['error'].get('data', {}).get('message', answer['error'])))
        return answer['result'], len(raw)

    def login(self):
        self.call('/web/session/authenticate', {'db': DB, 'login': 'admin', 'password': 'admin'})

    def model(self, model, method, args=None, kwargs=None):
        return self.call('/web/dataset/call_kw/%s/%s' % (model, method),
                         {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}})


def percentile(values, share):
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(share * (len(ordered) - 1)))))
    return ordered[index]


def timed(work, repeats=REPEATS):
    """(p50 ms, p95 ms, max ms, size of the answer in KB, rows) of a call made `repeats` times after one warm-up."""
    work()
    times, size, rows = [], 0, 0
    for _ in range(repeats):
        started = time.perf_counter()
        size, rows = work()
        times.append((time.perf_counter() - started) * 1000.0)
    return {'p50': round(statistics.median(times), 1), 'p95': round(percentile(times, 0.95), 1),
            'max': round(max(times), 1), 'kb': round(size / 1024.0, 1), 'rows': rows}


def measure(client):
    bus = client.model('bus.vehicle', 'search_read', [[['last_fix_time', '!=', False]]],
                       {'fields': ['id'], 'limit': 1})[0][0]['id']
    key = client.call('/bus_tracking/live', {})[0]['routes_key']
    since = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 4 * 3600))

    def live_refresh():                        # what the open map asks for every few seconds
        result, size = client.call('/bus_tracking/live', {'routes_key': key})
        return size, len(result['vehicles'])

    def live_first():
        result, size = client.call('/bus_tracking/live', {})
        return size, len(result['vehicles'])

    def history():
        rows, size = client.model('bus.position', 'search_read', [[['vehicle_id', '=', bus], ['fix_time', '>=', since]]],
                                  {'fields': ['latitude', 'longitude', 'speed', 'fix_time'], 'order': 'fix_time asc',
                                   'limit': 5000})
        return size, len(rows)

    def trip_list():                           # the first page of the list and its counter
        rows, size = client.model('bus.trip', 'search_read', [[]], {
            'fields': ['name', 'state', 'planned_start', 'route_id', 'vehicle_id', 'delay_end_min', 'detected_flags'],
            'order': 'planned_start desc', 'limit': 80})
        _count, size2 = client.model('bus.trip', 'search_count', [[]])
        return size + size2, len(rows)

    def indicators():
        result, size = client.model('bus.kpi', 'compute', [], {})
        return size, len(result['metrics'])

    def dashboard(days):
        def work():
            result, size = client.call('/bus_tracking/dashboard', {'days': days})
            return size, len(result['trips'])
        return work

    return {
        'live_refresh': timed(live_refresh), 'live_first_load': timed(live_first), 'bus_history_4h': timed(history),
        'trip_list': timed(trip_list), 'indicators_30d': timed(indicators),
        'dashboard_30d': timed(dashboard(30)), 'dashboard_90d': timed(dashboard(90)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--scenarios', default=SCENARIOS, help='positions:trips pairs, comma separated')
    parser.add_argument('--keep', action='store_true', help='do not remove the database and the server at the end')
    parser.add_argument('--out', default=OUT)
    args = parser.parse_args()
    scenarios = [tuple(int(n) for n in pair.split(':')) for pair in args.scenarios.split(',')]

    say('Database %s (a throwaway copy with the development lines and buses)' % DB)
    run('docker', 'rm', '-f', SERVER, check=False)
    psql('DROP DATABASE IF EXISTS %s' % DB, database='postgres')
    odoo_container('odoo', '-d', DB, '-i', 'bus_tracking', '--stop-after-init', '--without-demo=all', '--no-http',
                   '--load-language=es_EC',
                   *ODOO_ARGS)
    with open(os.path.join(ROOT, 'scripts', 'dev_seed.py'), encoding='utf-8') as handle:
        seed = handle.read()
    odoo_container('odoo', 'shell', '-d', DB, '--no-http', '--log-level=error', *ODOO_ARGS, stdin=seed)

    say('Odoo server on %s' % BASE)
    odoo_container('odoo', '-d', DB, '--workers=0', *ODOO_ARGS, detach=True)
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            if urllib.request.urlopen(BASE + '/web/login', timeout=5).status == 200:
                break
        except (urllib.error.URLError, OSError):
            time.sleep(2)
    else:
        raise SystemExit('The server did not start')
    client = Client()
    client.login()

    with open(os.path.join(ROOT, 'qa', 'rendimiento_volumen.sql'), encoding='utf-8') as handle:
        script = handle.read()
    results = []
    for positions, trips in scenarios:
        say('Scenario: %d positions, %d trips' % (positions, trips))
        lines = [line for line in psql(file_input=script, variables=[('positions', positions), ('trips', trips)])
                 .splitlines() if line.strip()]
        names = [n.strip() for n in lines[-4].split('|')]          # the last query: header, rule, row, "(1 row)"
        values = [int(v) for v in lines[-2].split('|')]
        measured = measure(client)
        results.append({'positions': positions, 'trips': trips, 'rows': dict(zip(names, values)),
                        'measures': measured})
        for name, figures in measured.items():
            flag = 'OK ' if figures['p95'] <= GOAL_MS else 'SLOW'
            print('  %s %-16s p50 %8.1f ms  p95 %8.1f ms  max %8.1f ms  %8.1f KB  %5d rows' % (
                flag, name, figures['p50'], figures['p95'], figures['max'], figures['kb'], figures['rows']))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump({'goal_p95_ms': GOAL_MS, 'repeats': REPEATS, 'results': results}, handle, indent=1)
        handle.write('\n')
    say('Written ' + os.path.relpath(args.out, ROOT))

    if not args.keep:
        run('docker', 'rm', '-f', SERVER, check=False)
        psql('DROP DATABASE IF EXISTS %s' % DB, database='postgres')
    slow = [(r['positions'], n) for r in results for n, f in r['measures'].items() if f['p95'] > GOAL_MS]
    if slow:
        print('Over the goal of %.0f ms (p95): %s' % (GOAL_MS, slow))
    return 1 if slow else 0


if __name__ == '__main__':
    sys.exit(main())
