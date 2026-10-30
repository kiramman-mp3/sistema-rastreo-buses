"""Full quality run, from nothing: prepares the environment and runs every check.

    python -X utf8 qa/ejecutar_todo.py                 # everything
    python -X utf8 qa/ejecutar_todo.py suite           # only the live suite (also: auditoria, metricas, odoo)
    python -X utf8 qa/ejecutar_todo.py --limpiar       # remove the QA server and databases

It starts Postgres, creates the database buses_qa with the module installed, starts the dedicated server
qa-odoo, restarts it before measuring (the rate limits live in memory), runs the Odoo tests with coverage in
a throwaway database and then the live suite, the audit and the metrics. Only Docker and Python are needed.
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from common import BASE, DB, OUT

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
QA_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER = 'qa-odoo'
UNIT_DB = 'buses_unit'
PORT = BASE.rsplit(':', 1)[-1]
STEPS = ['odoo', 'suite', 'auditoria', 'metricas']

# Runs inside the Odoo image: Odoo tests under coverage.py, in a database that is dropped afterwards.
COVERAGE_SCRIPT = (
    'pip3 install -q coverage && '
    'coverage run --branch --data-file=/tmp/.coverage --source=/mnt/extra-addons/bus_tracking --omit="*/tests/*" '
    '/usr/bin/odoo -d {db} --db_host $HOST --db_user $USER --db_password $PASSWORD -i bus_tracking '
    '--test-enable --test-tags /bus_tracking --stop-after-init --without-demo=all --log-level=test '
    '> /out/odoo_test.log 2>&1; '
    'coverage report --data-file=/tmp/.coverage -m > /out/cobertura.txt; '
    'coverage json --data-file=/tmp/.coverage -o /out/coverage.json -q'
)


def say(text):
    print('==> ' + text, flush=True)


def docker(*args, check=True):
    """Run a docker command from the project folder and return its output."""
    result = subprocess.run(['docker', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
                            errors='replace')
    if check and result.returncode:
        raise SystemExit('Fallo: docker %s\n%s%s' % (' '.join(args), result.stdout[-1500:], result.stderr[-1500:]))
    return result


def psql(sql, database='postgres'):
    return docker('compose', 'exec', '-T', 'db', 'psql', '-U', 'odoo', '-d', database, '-tAc', sql).stdout.strip()


def wait_for(description, probe, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if probe():
            return
        time.sleep(2)
    raise SystemExit('Se agotó la espera de: ' + description)


def ready():
    try:
        return urllib.request.urlopen(BASE + '/web/login', timeout=5).status == 200
    except (urllib.error.URLError, OSError):
        return False


def database_exists(name):
    return psql("SELECT 1 FROM pg_database WHERE datname='%s'" % name) == '1'


def drop_database(name):
    psql('DROP DATABASE IF EXISTS %s WITH (FORCE)' % name)


def server_state():
    result = docker('inspect', '-f', '{{.State.Running}}', SERVER, check=False)
    if result.returncode:
        return 'missing'
    return 'running' if result.stdout.strip() == 'true' else 'stopped'


def prepare_database():
    say('Postgres')
    if not os.path.exists(os.path.join(ROOT, '.env')):
        say('No hay .env; se usan los valores por defecto del docker-compose.yml')
    docker('compose', 'up', '-d', 'db')
    wait_for('Postgres', lambda: docker('compose', 'exec', '-T', 'db', 'pg_isready', '-U', 'odoo',
                                        check=False).returncode == 0, 90)
    if database_exists(DB):
        return
    say('Creando la base %s con el módulo instalado (unos minutos)' % DB)
    docker('compose', 'run', '--rm', '--no-deps', 'odoo', 'odoo', '-d', DB, '-i', 'bus_tracking',
           '--stop-after-init', '--without-demo=all')


def prepare_server(restart):
    """Start qa-odoo if needed; with `restart`, always begin from a clean process."""
    state = server_state()
    if state == 'missing':
        say('Creando el servidor %s en el puerto %s' % (SERVER, PORT))
        docker('compose', 'run', '-d', '--no-deps', '--name', SERVER, '-p', '%s:8069' % PORT, 'odoo',
               'odoo', '-d', DB, '--db-filter', '^%s$' % DB)
    elif state == 'stopped':
        say('Arrancando %s' % SERVER)
        docker('start', SERVER)
    elif restart:
        say('Reiniciando %s (límites de uso en limpio)' % SERVER)
        docker('restart', SERVER)
    wait_for('el servidor %s en %s' % (SERVER, BASE), ready, 180)


def run_unit_tests():
    say('Pruebas de Odoo con cobertura, en la base desechable %s' % UNIT_DB)
    os.makedirs(OUT, exist_ok=True)
    drop_database(UNIT_DB)
    docker('compose', 'run', '--rm', '--no-deps', '--user', 'root', '-v', '%s:/out' % os.path.abspath(OUT),
           'odoo', 'sh', '-c', COVERAGE_SCRIPT.format(db=UNIT_DB))
    drop_database(UNIT_DB)
    tail = open(os.path.join(OUT, 'odoo_test.log'), encoding='utf-8', errors='replace').read().splitlines()[-3:]
    print('\n'.join(tail))


def run_script(name):
    """Run qa/<name>.py with its output saved as evidence; return its exit code."""
    say('%s.py' % name)
    log = os.path.join(OUT, name + '.log')
    script = 'qa_suite' if name == 'suite' else name
    with open(log, 'w', encoding='utf-8') as handle:
        code = subprocess.run([sys.executable, '-X', 'utf8', '-u', os.path.join(QA_DIR, script + '.py')],
                              cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT).returncode
    print('\n'.join(open(log, encoding='utf-8', errors='replace').read().splitlines()[-4:]))
    return code


def clean():
    say('Eliminando %s y las bases %s y %s' % (SERVER, DB, UNIT_DB))
    docker('rm', '-f', SERVER, check=False)
    if subprocess.run(['docker', 'compose', 'ps', '-q', 'db'], cwd=ROOT, capture_output=True,
                      text=True).stdout.strip():
        drop_database(DB)
        drop_database(UNIT_DB)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('pasos', nargs='*', metavar='paso',
                        help='uno o más de: %s (por defecto, todos)' % ', '.join(STEPS))
    parser.add_argument('--limpiar', action='store_true', help='elimina el servidor y las bases de pruebas')
    args = parser.parse_args()
    unknown = [p for p in args.pasos if p not in STEPS]
    if unknown:
        parser.error('paso desconocido: %s (usa: %s)' % (', '.join(unknown), ', '.join(STEPS)))
    if docker('info', check=False).returncode:
        raise SystemExit('Docker no responde: abre Docker Desktop y vuelve a intentarlo.')
    if args.limpiar:
        return clean()
    steps = [s for s in STEPS if s in args.pasos] or STEPS
    os.makedirs(OUT, exist_ok=True)
    prepare_database()
    if 'odoo' in steps:
        run_unit_tests()
    failed = []
    if {'suite', 'auditoria'} & set(steps):
        prepare_server(restart=True)
    for name in ('suite', 'auditoria'):
        if name in steps and run_script(name) and name != 'suite':
            failed.append(name)       # the suite exits non-zero when a case fails: that is a result, not an error
    if 'metricas' in steps and run_script('metricas'):
        failed.append('metricas')
    say('Listo. Evidencias en %s' % os.path.abspath(OUT))
    if failed:
        raise SystemExit('Fallaron: ' + ', '.join(failed))


if __name__ == '__main__':
    main()
