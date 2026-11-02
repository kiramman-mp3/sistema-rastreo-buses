"""Shared helpers for the live quality checks (suite, audit and metrics).

The checks talk to a running Odoo (default http://localhost:8071, database buses_qa)
through HTTP and XML-RPC, like a phone, a passenger or an administrator would.
"""
import json
import math
import os
import statistics
import subprocess
import time
import xmlrpc.client
from datetime import datetime, timedelta, timezone

BASE = os.environ.get('QA_BASE', 'http://localhost:8071')
DB = os.environ.get('QA_DB', 'buses_qa')
ADMIN_LOGIN = os.environ.get('QA_ADMIN_LOGIN', 'admin')
ADMIN_PASSWORD = os.environ.get('QA_ADMIN_PASSWORD', 'admin')
SECRET = 'qa-secret'
WEBHOOK = BASE + '/bus_tracking/traccar/webhook'
OUT = os.environ.get('QA_OUT') or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, 'docs', 'calidad', 'evidencias')

# Route used by every check: three stops in Ambato, about 1.5 km apart, 80 m arrival radius.
STOPS = [
    ('QA Terminal', -1.2700, -78.6280),
    ('QA Plaza', -1.2600, -78.6200),
    ('QA Campus', -1.2500, -78.6110),
]
DEVICE_BASE = 100          # bus QA-01 is Traccar device 101, QA-02 is 102, ...
BUS_COUNT = 45


class Odoo:
    """XML-RPC session of the administrator, used to prepare data and to read back the truth."""

    def __init__(self):
        common = xmlrpc.client.ServerProxy(BASE + '/xmlrpc/2/common')
        self.uid = common.authenticate(DB, ADMIN_LOGIN, ADMIN_PASSWORD, {})
        if not self.uid:
            raise SystemExit('Cannot log in to %s as %s' % (BASE, ADMIN_LOGIN))
        self.models = xmlrpc.client.ServerProxy(BASE + '/xmlrpc/2/object', allow_none=True)

    def call(self, model, method, *args, **kwargs):
        return self.models.execute_kw(DB, self.uid, ADMIN_PASSWORD, model, method, list(args), kwargs)

    def search_count(self, model, domain):
        return self.call(model, 'search_count', domain)

    def read(self, model, domain, fields, **kw):
        return self.call(model, 'search_read', domain, fields=fields, **kw)


def iso(seconds_ago=0.0):
    """UTC timestamp in the format Traccar sends."""
    moment = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ')


def position(device, fix_time, lat, lon, speed_knots=0.0, course=90.0):
    return {
        'position': {'deviceId': device, 'fixTime': fix_time, 'latitude': lat, 'longitude': lon,
                     'speed': speed_knots, 'course': course},
        'device': {'id': device},
    }


# -- statistics ------------------------------------------------------------------------------
def percentile(values, pct):
    """Nearest-rank percentile."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[rank - 1]


def describe(values):
    values = list(values)
    if not values:
        return {'n': 0, 'mean': 0.0, 'min': 0.0, 'max': 0.0, 'stdev': 0.0, 'variance': 0.0, 'cv': 0.0,
                'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
    mean = statistics.fmean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        'n': len(values), 'mean': mean, 'min': min(values), 'max': max(values),
        'stdev': stdev, 'variance': stdev ** 2, 'cv': (stdev / mean * 100.0) if mean else 0.0,
        'p50': percentile(values, 50), 'p95': percentile(values, 95), 'p99': percentile(values, 99),
    }


def save_json(name, data):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return path


def load_json(name):
    with open(os.path.join(OUT, name), encoding='utf-8') as handle:
        return json.load(handle)


class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self.start


def prepare(odoo):
    """Leave the database with the QA route, the QA buses and the webhook secret; remove old QA data."""
    for model, domain in (
            ('bus.complaint', [('description', 'like', 'QA-')]),
            ('bus.vehicle', [('name', 'like', 'QA-')]),
            ('bus.route', [('code', 'like', 'QA')])):
        ids = odoo.call(model, 'search', domain, context={'active_test': False})
        if ids:
            odoo.call(model, 'unlink', ids)
    odoo.call('ir.config_parameter', 'set_param', 'bus_tracking.webhook_secret', SECRET)
    odoo.call('ir.config_parameter', 'set_param', 'bus_tracking.stale_minutes', '10')
    # The live suite and the audit post positions by webhook for buses without a driver on shift.
    odoo.call('ir.config_parameter', 'set_param', 'bus_tracking.accept_without_shift', '1')
    route = odoo.call('bus.route', 'create', [{
        'name': 'QA Troncal', 'code': 'QA1', 'public': True, 'color': '#1e5560',
        'stop_ids': [(0, 0, {'sequence': i * 10, 'name': name, 'latitude': lat, 'longitude': lon, 'radius': 80})
                     for i, (name, lat, lon) in enumerate(STOPS, start=1)],
    }])[0]
    private = odoo.call('bus.route', 'create', [{'name': 'QA Privada', 'code': 'QA-PRIV', 'public': False}])[0]
    buses = odoo.call('bus.vehicle', 'create', [
        {'name': 'QA-%02d' % n, 'route_id': route, 'traccar_device_id': DEVICE_BASE + n,
         'plate': 'QAPLATE%02d' % n} for n in range(1, BUS_COUNT + 1)])
    return {'route': route, 'private': private, 'buses': buses}


def psql(sql, db=None, container='sistema-rastreo-buses-db-1'):
    """One value (or a text table with -At) from the QA database, straight from Postgres."""
    out = subprocess.run(['docker', 'exec', container, 'psql', '-U', 'odoo', '-d', db or DB, '-At', '-c', sql],
                         capture_output=True, text=True, encoding='utf-8')
    return out.stdout.strip()


OUT_OF_RANGE = "SELECT count(*) FROM bus_position WHERE latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180"
