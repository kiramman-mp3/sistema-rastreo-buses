"""Audit of 1 000 randomly generated requests over 15 areas of bus_tracking (seeded, so it can be repeated).

Each request has the expected result decided before it is sent; a request passes when the answer is
one of the expected HTTP statuses (and, for the webhook, nothing broke on the server side).

    python -X utf8 qa/auditoria.py

Needs the data left by qa_suite.py (route QA1 and buses QA-01..QA-45). Writes auditoria.json.
"""
import json
import random
import re
import sys
import time

import requests

from common import BASE, DEVICE_BASE, OUT_OF_RANGE, SECRET, WEBHOOK, Odoo, describe, iso, position, psql, save_json

SEED = 20261028
TOTAL = 1000
HDR = {'Content-Type': 'application/json', 'X-Webhook-Secret': SECRET}
NO_SECRET = {'Content-Type': 'application/json'}

rng = random.Random(SEED)
FEED_HITS = []          # times of the requests that count against the public feed's 60-per-minute limit
used_times = set()


def fresh_time():
    """A GPS time that was never used before in the audit (the database refuses duplicates)."""
    while True:
        seconds = rng.randint(3600 * 2, 3600 * 20)            # 2 to 20 hours ago: out of the live view of the portal
        if seconds not in used_times:
            used_times.add(seconds)
            return iso(seconds)


def device():
    return DEVICE_BASE + rng.randint(1, 45)


def ambato():
    return round(rng.uniform(-1.30, -1.20), 6), round(rng.uniform(-78.66, -78.58), 6)


def spoofed():
    return {'X-Forwarded-For': '10.%d.%d.%d' % (rng.randint(1, 250), rng.randint(1, 250), rng.randint(1, 250))}


class Probe:
    def __init__(self, area, method, url, expected, **kwargs):
        self.area, self.method, self.url, self.expected, self.kwargs = area, method, url, set(expected), kwargs


def web(payload, headers=HDR):
    body = payload if isinstance(payload, (str, bytes)) else json.dumps(payload)
    return dict(data=body, headers=headers)


# -- the 15 areas, each builds one random probe --------------------------------------------------
def a01():
    lat, lon = ambato()
    return Probe('01 Webhook: posición válida', 'POST', WEBHOOK, {200},
                 **web(position(device(), fresh_time(), lat, lon, round(rng.uniform(0, 45), 1), rng.randint(0, 359))))


def a02():
    lat, lon = ambato()
    headers = rng.choice([NO_SECRET, {**NO_SECRET, 'X-Webhook-Secret': 'x' * rng.randint(1, 40)}])
    return Probe('02 Webhook: secreto ausente o falso', 'POST', WEBHOOK, {403},
                 **web(position(device(), fresh_time(), lat, lon), headers=headers))


def a03():
    junk = rng.choice(['', 'no es json', '{', '{"position": ', '<xml/>', '\x00\x01', 'null null', '{{{{'])
    return Probe('03 Webhook: cuerpo que no es JSON', 'POST', WEBHOOK, {400}, **web(junk))


def a04():
    return Probe('04 Webhook: JSON que no es un objeto', 'POST', WEBHOOK, {200, 400},
                 **web(rng.choice([[], [1, 2], 5, 'texto', None, True])))


def a05():
    lat, lon = ambato()
    return Probe('05 Webhook: dispositivo desconocido', 'POST', WEBHOOK, {200},
                 **web(position(rng.randint(5000, 99999), fresh_time(), lat, lon)))


def a06():
    """Values a broken or hostile sender could put in the position. A server error here is a defect."""
    lat, lon = ambato()
    kind = rng.choice(['lat_high', 'lon_high', 'lat_text', 'time_text', 'lat_null', 'time_missing'])
    payload = position(device(), fresh_time(), lat, lon)
    pos = payload['position']
    if kind == 'lat_high':
        pos['latitude'] = rng.choice([91, 95, 180, 1e6])
    elif kind == 'lon_high':
        pos['longitude'] = rng.choice([181, 360, -500, 1e6])
    elif kind == 'lat_text':
        pos['latitude'] = rng.choice(['abc', '', 'NaN'])
    elif kind == 'time_text':
        pos['fixTime'] = rng.choice(['ayer', 'hoy 10:00', '2026-13-45T99:00:00Z'])
    elif kind == 'lat_null':
        pos['latitude'] = None
    else:
        pos.pop('fixTime')
    probe = Probe('06 Webhook: valores inválidos en la posición', 'POST', WEBHOOK, {200, 400, 422}, **web(payload))
    probe.note = kind
    return probe


def a07():
    return Probe('07 Webhook: método incorrecto', rng.choice(['GET', 'PUT', 'DELETE']), WEBHOOK, {404, 405},
                 headers={'X-Webhook-Secret': SECRET})


def a08():
    return Probe('08 Portal: lista de rutas', 'GET', BASE + '/rutas', {200}, params={'lang': rng.choice(['es', 'en', 'qu', 'zz'])})


def a09():
    return Probe('09 Portal: mapa de una ruta pública', 'GET', BASE + '/rutas/QA1', {200}, params={'lang': rng.choice(['es', 'en'])})


def a10():
    code = rng.choice(['NOPE', 'QA-PRIV', 'qa1', '../etc/passwd', 'x' * 200, "QA1' OR 1=1--", '%00'])
    return Probe('10 Portal: ruta inexistente, privada o hostil', 'GET', BASE + '/rutas/' + requests.utils.quote(code, safe=''), {404})


def a11():
    return Probe('11 Feed público de buses', 'GET', BASE + '/rutas/QA1/buses.json', {200}, headers=spoofed())


def a12():
    code = rng.choice(['NOPE', 'QA-PRIV', 'zzz'])
    return Probe('12 Feed de ruta inexistente o privada', 'GET', BASE + '/rutas/%s/buses.json' % code, {404}, headers=spoofed())


def a13():
    return Probe('13 Salud del servicio', 'GET', BASE + '/bus_tracking/health', {200, 503})


def a14():
    return Probe('14 Formulario de quejas y páginas públicas', 'GET', BASE + rng.choice(['/quejas', '/quejas?ruta=QA1', '/quejas/gracias', '/quejas/gracias?f=Q-00001&c=0', '/', '/inicio']),
                 {200})


def a15():
    """Invalid complaint submissions (these never store anything and never use the hourly allowance)."""
    variant = rng.choice(['short', 'email', 'phone', 'nocsrf', 'trap', 'forged', 'huge'])
    data = {'csrf_token': SESSION['csrf'], 't': SESSION['t'], 'route': 'QA1', 'bus': '', 'kind': rng.choice(['delay', 'safety', 'hack']),
            'description': 'QA-AUD descripción suficientemente larga para pasar', 'email': '', 'phone': '', 'website': ''}
    expected = {400}
    if variant == 'short':
        data['description'] = 'corto'
    elif variant == 'email':
        data['email'] = rng.choice(['x', 'a@b', '@@', 'sin arroba.com'])
    elif variant == 'phone':
        data['phone'] = rng.choice(['abc', '12', '<script>'])
    elif variant == 'nocsrf':
        data['csrf_token'] = ''
    elif variant == 'trap':
        data['website'] = 'http://spam.example'
        expected = {303}
    elif variant == 'forged':
        data['t'] = '1.' + 'a' * 40
        expected = {303}
    else:
        data['description'] = 'QA-AUD ' + 'z' * 25000
        expected = {413}
    return Probe('15 Quejas: envíos inválidos', 'POST', BASE + '/quejas', expected, data=data, cookies=SESSION['cookies'])


AREAS = [a01, a02, a03, a04, a05, a06, a07, a08, a09, a10, a11, a12, a13, a14, a15]
SESSION = {}


def main():
    odoo = Odoo()
    before = odoo.search_count('bus.position', [])
    complaints_before = odoo.search_count('bus.complaint', [])
    invalid_before = int(psql(OUT_OF_RANGE))
    session = requests.Session()
    html = session.get(BASE + '/quejas', timeout=30).text
    SESSION.update(csrf=re.search(r'name="csrf_token" value="([^"]+)"', html).group(1),
                   t=re.search(r'name="t" value="([^"]+)"', html).group(1), cookies=session.cookies)
    time.sleep(62)          # the suite's last test emptied the feed's one-minute allowance; let it recover

    rows, started = [], time.time()
    for _ in range(TOTAL):
        probe = rng.choice(AREAS)()
        if probe.url.endswith('/buses.json'):
            # The feed refuses more than 60 requests a minute per address (that is tested in the suite):
            # keep a margin so the audit measures the feed and not the limiter.
            FEED_HITS[:] = [t for t in FEED_HITS if time.monotonic() - t < 61]
            while len(FEED_HITS) >= 55:
                time.sleep(max(0.5, 61 - (time.monotonic() - FEED_HITS[0])))
                FEED_HITS[:] = [t for t in FEED_HITS if time.monotonic() - t < 61]
            FEED_HITS.append(time.monotonic())
        began = time.perf_counter()
        try:
            response = requests.request(probe.method, probe.url, timeout=60, allow_redirects=False, **probe.kwargs)
            status = response.status_code
        except requests.RequestException:
            status = 0
        elapsed = time.perf_counter() - began
        rows.append({'area': probe.area, 'status': status, 'esperado': sorted(probe.expected), 'ok': status in probe.expected,
                     'tiempo': elapsed, 'nota': getattr(probe, 'note', '')})

    # Does a forged X-Forwarded-For defeat the per-address limit when Odoo is reached without a proxy?
    # A line that does not exist: cached answers of a real line never count towards the limit.
    time.sleep(62)
    spoof_codes = [requests.get(BASE + '/rutas/QA-NOPE/buses.json', headers=spoofed(), timeout=30).status_code
                   for _ in range(70)]

    # A position with impossible coordinates answers 200 (that status is allowed), so the damage is counted in the data.
    stored_invalid = int(psql(OUT_OF_RANGE)) - invalid_before
    summary = {}
    for row in rows:
        item = summary.setdefault(row['area'], {'n': 0, 'fail': 0, 'tiempos': []})
        item['n'] += 1
        item['fail'] += 0 if row['ok'] else 1
        item['tiempos'].append(row['tiempo'])
    areas = [{'area': name, 'n': v['n'], 'fail': v['fail'], **{k: val for k, val in describe(v['tiempos']).items() if k != 'n'}}
             for name, v in sorted(summary.items())]
    everything = describe([r['tiempo'] for r in rows])
    threshold = everything['mean'] + 3 * everything['stdev']
    failures = [r for r in rows if not r['ok']]
    by_note = {}
    for r in failures:
        by_note[r['nota'] or r['area']] = by_note.get(r['nota'] or r['area'], 0) + 1
    if stored_invalid:
        by_note['coordenadas fuera de rango guardadas'] = stored_invalid
    probes_by_note = {}
    for r in rows:
        if r['nota']:
            probes_by_note[r['nota']] = probes_by_note.get(r['nota'], 0) + 1
    result = {
        'semilla': SEED, 'total': len(rows), 'fallos': len(failures) + stored_invalid, 'fallos_estado': len(failures), 'guardadas_invalidas': stored_invalid,
        'pct_error': 100.0 * (len(failures) + stored_invalid) / len(rows), 'sondeos_por_nota': probes_by_note,
        'segundos': time.time() - started, 'tiempo': everything, 'umbral_atipico': threshold,
        'atipicos': sum(1 for r in rows if r['tiempo'] > threshold),
        'sobre_p95': sum(1 for r in rows if r['tiempo'] > everything['p95']),
        'posiciones_nuevas': odoo.search_count('bus.position', []) - before,
        'quejas_nuevas': odoo.search_count('bus.complaint', []) - complaints_before,
        'estados_5xx': sum(1 for r in rows if r['status'] >= 500),
        # A 503 from /health when no bus reported recently is an expected answer, not an error.
        'estados_5xx_inesperados': sum(1 for r in rows if r['status'] >= 500 and not r['ok']),
        'areas': areas, 'fallos_por_causa': by_note,
        'muestra_fallos': failures[:15],
        'tiempos': [round(r['tiempo'], 5) for r in rows],
        'suplantacion_xff': {'peticiones': len(spoof_codes), 'respuestas_429': spoof_codes.count(429)},
    }
    save_json('auditoria.json', result)
    print('%d de %d correctas (%.2f %% de error). Media %.4f s, máx. %.4f s. 5xx: %d. Fallos por causa: %s' % (
        len(rows) - result['fallos'], len(rows), result['pct_error'], everything['mean'], everything['max'], result['estados_5xx'], by_note))
    print('Con X-Forwarded-For distinto en cada petición: %d respuestas 429 de %d' % (spoof_codes.count(429), len(spoof_codes)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
