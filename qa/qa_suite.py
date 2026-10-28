"""Live quality suite for bus_tracking: functional (F), error (E), performance (P) and usability (U) checks.

Run against a dedicated Odoo that was just (re)started, because two limits live in memory
(5 complaints per hour and 60 bus lists per minute):

    docker restart qa-odoo
    python -X utf8 qa/qa_suite.py

Writes docs/calidad/evidencias/suite.json and suite.log.
"""
import concurrent.futures as futures
import json
import re
import sys
import time
import traceback

import requests

from common import (BASE, DB, DEVICE_BASE, SECRET, STOPS, WEBHOOK, Odoo, Timer, describe, iso, position, prepare,
                    save_json)

HEADERS_JSON = {'Content-Type': 'application/json'}
HDR_SECRET = {'Content-Type': 'application/json', 'X-Webhook-Secret': SECRET}
LEAKS = ('Traceback', 'psycopg2', 'IntegrityError', 'File "/', 'odoo.exceptions', 'SELECT ', 'INSERT ')

RESULTS = []
STATE = {'complaints_accepted': 0}
_timings = []


class Fail(Exception):
    pass


def check(condition, message):
    if not condition:
        raise Fail(message)


def req(method, url, **kwargs):
    """HTTP request whose duration is added to the running test."""
    kwargs.setdefault('timeout', 30)
    kwargs.setdefault('allow_redirects', False)
    with Timer() as timer:
        response = requests.request(method, url, **kwargs)
    _timings.append(timer.elapsed)
    return response


def hook(payload, headers=None, query=''):
    body = payload if isinstance(payload, (str, bytes)) else json.dumps(payload)
    return req('POST', WEBHOOK + query, data=body, headers=headers or HDR_SECRET)


def case(code, kind, objective, entry, expected):
    def decorator(fn):
        fn.meta = dict(id=code, tipo=kind, objetivo=objective, entrada=entry, esperado=expected)
        CASES.append(fn)
        return fn
    return decorator


CASES = []


def run_case(fn, ctx):
    _timings.clear()
    record = dict(fn.meta)
    started = time.perf_counter()
    try:
        info = fn(ctx) or {}
        record.update(estado='PASS', error='Ninguno', **{k: v for k, v in info.items()})
    except Fail as exc:
        record.update(estado='FAIL', error=str(exc), obtenido=str(exc), mensaje='')
    except Exception as exc:  # noqa: BLE001 - a crash of the check is a failed check, with the trace in the log
        record.update(estado='FAIL', error='%s: %s' % (type(exc).__name__, exc), obtenido=repr(exc), mensaje='')
        print(traceback.format_exc())
    record['tiempo'] = sum(_timings) if _timings else time.perf_counter() - started
    RESULTS.append(record)
    print('%-4s %-4s %.4f s  %s' % (record['id'], record['estado'], record['tiempo'], record.get('obtenido', '')[:90]))


# -- helpers to read the truth back ------------------------------------------------------------
def bus_of(ctx, n):
    return ctx['odoo'].read('bus.vehicle', [('name', '=', 'QA-%02d' % n)],
                            ['last_latitude', 'last_longitude', 'last_speed', 'last_fix_time', 'current_stop_id'])[0]


def positions_of(ctx, n):
    return ctx['odoo'].search_count('bus.position', [('vehicle_id.name', '=', 'QA-%02d' % n)])


def all_positions(ctx):
    return ctx['odoo'].search_count('bus.position', [('vehicle_id.name', 'like', 'QA-')])


def complaint_count(ctx):
    return ctx['odoo'].search_count('bus.complaint', [])


def device(n):
    return DEVICE_BASE + n


MID = (-1.2650, -78.6240)       # between the first two stops, well outside every 80 m radius


def form(session, lang='es', path='/quejas?ruta=QA1'):
    html = session.get(BASE + path, headers={'Accept-Language': lang}, timeout=30).text
    return (re.search(r'name="csrf_token" value="([^"]+)"', html).group(1),
            re.search(r'name="t" value="([^"]+)"', html).group(1))


def complaint(session, csrf, token, description, lang='es', **extra):
    data = {'csrf_token': csrf, 't': token, 'route': 'QA1', 'bus': '', 'kind': 'delay',
            'description': description, 'email': '', 'phone': '', 'website': ''}
    data.update(extra)
    return req('POST', BASE + '/quejas', data=data, headers={'Accept-Language': lang}, cookies=session.cookies)


# ================================================================================================
# Functional
# ================================================================================================
@case('F1', 'Funcional', 'Guardar una posición válida enviada por el webhook (secreto en cabecera)',
      'POST con deviceId 101, lat -1.2650, lon -78.6250', 'HTTP 200; 1 posición; el bus queda en esa posición')
def f1(ctx):
    r = hook(position(device(1), iso(60), -1.2650, -78.6250, 3.0))
    check(r.status_code == 200, 'HTTP %s' % r.status_code)
    bus = bus_of(ctx, 1)
    check(positions_of(ctx, 1) == 1, 'posiciones guardadas: %s' % positions_of(ctx, 1))
    check(abs(bus['last_latitude'] + 1.2650) < 1e-6 and abs(bus['last_longitude'] + 78.6250) < 1e-6, 'posición del bus distinta')
    return dict(obtenido='HTTP 200; 1 posición; bus en (%.4f, %.4f)' % (bus['last_latitude'], bus['last_longitude']),
                mensaje='Sin cuerpo (200)')


@case('F2', 'Funcional', 'Convertir la velocidad de nudos a km/h', 'speed = 10 nudos', 'last_speed = 18,52 km/h')
def f2(ctx):
    check(hook(position(device(2), iso(60), *MID, speed_knots=10.0)).status_code == 200, 'webhook rechazó la posición')
    speed = bus_of(ctx, 2)['last_speed']
    check(abs(speed - 18.52) < 0.01, 'velocidad %.3f' % speed)
    return dict(obtenido='%.2f km/h' % speed, mensaje='Sin cuerpo (200)')


@case('F3', 'Funcional', 'Ignorar una posición duplicada (mismo bus y hora GPS)', 'La misma posición enviada 2 veces',
      '1 sola posición guardada')
def f3(ctx):
    payload = position(device(3), iso(60), *MID, speed_knots=1.0)
    check(hook(payload).status_code == 200 and hook(payload).status_code == 200, 'el webhook no respondió 200')
    count = positions_of(ctx, 3)
    check(count == 1, 'posiciones guardadas: %d' % count)
    return dict(obtenido='1 posición tras 2 envíos', mensaje='Sin cuerpo (200)')


@case('F4', 'Funcional', 'Una posición más antigua no sobrescribe el estado del bus',
      'Posición de hace 100 s y luego una de hace 500 s', 'last_fix_time y última posición no cambian; se guardan 2')
def f4(ctx):
    hook(position(device(4), iso(100), -1.2650, -78.6240))
    before = bus_of(ctx, 4)
    hook(position(device(4), iso(500), -1.2610, -78.6210))
    after = bus_of(ctx, 4)
    check(before['last_fix_time'] == after['last_fix_time'] and before['last_latitude'] == after['last_latitude'],
          'la posición antigua cambió el estado')
    check(positions_of(ctx, 4) == 2, 'posiciones: %d' % positions_of(ctx, 4))
    return dict(obtenido='Estado intacto; 2 posiciones guardadas', mensaje='Sin cuerpo (200)')


@case('F5', 'Funcional', 'Registrar la llegada a una parada una sola vez mientras el bus sigue dentro del radio',
      'Dos posiciones consecutivas en la parada QA Terminal', '1 llegada; el bus queda en esa parada')
def f5(ctx):
    name, lat, lon = STOPS[0]
    hook(position(device(5), iso(300), lat, lon))
    hook(position(device(5), iso(290), lat, lon))
    arrivals = ctx['odoo'].search_count('bus.stop.arrival', [('vehicle_id.name', '=', 'QA-05')])
    check(arrivals == 1, 'llegadas: %d' % arrivals)
    check(bus_of(ctx, 5)['current_stop_id'][1] == name, 'parada actual distinta')
    return dict(obtenido='1 llegada en "%s"' % name, mensaje='Sin cuerpo (200)')


@case('F6', 'Funcional', 'Registrar un recorrido completo entre la primera y la última parada',
      'Salida de QA Terminal, tramo intermedio y llegada a QA Campus', '1 recorrido terminado de Terminal a Campus')
def f6(ctx):
    hook(position(device(6), iso(600), STOPS[0][1], STOPS[0][2]))
    hook(position(device(6), iso(500), *MID, speed_knots=15.0))
    hook(position(device(6), iso(300), STOPS[2][1], STOPS[2][2]))
    runs = ctx['odoo'].read('bus.run', [('vehicle_id.name', '=', 'QA-06')], ['state', 'origin_stop_id', 'destination_stop_id'])
    check(len(runs) == 1 and runs[0]['state'] == 'done', 'recorridos: %r' % runs)
    check(runs[0]['origin_stop_id'][1] == STOPS[0][0] and runs[0]['destination_stop_id'][1] == STOPS[2][0], 'extremos incorrectos')
    return dict(obtenido='Recorrido "done": %s → %s' % (runs[0]['origin_stop_id'][1], runs[0]['destination_stop_id'][1]),
                mensaje='Sin cuerpo (200)')


@case('F7', 'Funcional', 'Abrir y cerrar la alerta de exceso de velocidad', '40 nudos (74 km/h) y luego 5 nudos',
      'Alerta "speeding" abierta con máximo ≈74 km/h y luego cerrada')
def f7(ctx):
    hook(position(device(7), iso(200), *MID, speed_knots=40.0))
    opened = ctx['odoo'].read('bus.alert', [('vehicle_id.name', '=', 'QA-07'), ('kind', '=', 'speeding')], ['state', 'max_speed'])
    check(len(opened) == 1 and opened[0]['state'] == 'open' and abs(opened[0]['max_speed'] - 74.08) < 0.1, 'alerta: %r' % opened)
    hook(position(device(7), iso(100), *MID, speed_knots=5.0))
    closed = ctx['odoo'].read('bus.alert', [('vehicle_id.name', '=', 'QA-07'), ('kind', '=', 'speeding')], ['state'])
    check(closed[0]['state'] == 'closed', 'la alerta no se cerró')
    return dict(obtenido='Abierta (máx. %.1f km/h) y cerrada' % opened[0]['max_speed'], mensaje='Sin cuerpo (200)')


@case('F8', 'Funcional', 'La página pública /rutas lista solo las rutas públicas', 'GET /rutas',
      'HTTP 200; aparece "QA Troncal"; no aparece "QA Privada"')
def f8(ctx):
    r = req('GET', BASE + '/rutas')
    check(r.status_code == 200, 'HTTP %s' % r.status_code)
    check('QA Troncal' in r.text and 'QA Privada' not in r.text, 'lista incorrecta')
    return dict(obtenido='HTTP 200; solo la ruta pública', mensaje='Página HTML')


@case('F9', 'Funcional', 'El feed público expone solo nombre, posición, rumbo y estado',
      'GET /rutas/QA1/buses.json', 'Claves exactas {name, lat, lon, course, status}; sin placa ni velocidad')
def f9(ctx):
    r = req('GET', BASE + '/rutas/QA1/buses.json')
    check(r.status_code == 200, 'HTTP %s' % r.status_code)
    data = r.json()
    check(data['buses'], 'ningún bus visible')
    keys = {frozenset(bus) for bus in data['buses']}
    check(keys == {frozenset({'name', 'lat', 'lon', 'course', 'status'})}, 'claves: %r' % keys)
    check('QAPLATE' not in r.text, 'la placa aparece en el feed')
    return dict(obtenido='%d buses; 5 claves; sin placa' % len(data['buses']), mensaje='JSON')


@case('F10', 'Funcional', 'Guardar una queja válida y entregar un folio', 'Formulario con descripción de 60 caracteres y correo',
      'HTTP 303 a /quejas/gracias?f=Q-…; queja en estado "new"')
def f10(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    r = complaint(session, csrf, token, 'QA-F10 El bus llegó con veinte minutos de retraso esta mañana.', email='qa@example.com')
    check(r.status_code == 303 and 'f=Q-' in r.headers.get('Location', ''), 'HTTP %s %s' % (r.status_code, r.headers.get('Location')))
    STATE['complaints_accepted'] += 1
    rows = ctx['odoo'].read('bus.complaint', [('description', 'like', 'QA-F10')], ['name', 'state', 'contact_email'])
    check(len(rows) == 1 and rows[0]['state'] == 'new', 'queja: %r' % rows)
    return dict(obtenido='303; folio %s; estado new' % rows[0]['name'], mensaje='Redirección a la página de gracias')


@case('F11', 'Funcional', 'Aceptar una queja anónima (sin correo ni teléfono)', 'Formulario solo con descripción',
      'HTTP 303 con c=0 (no podemos responder)')
def f11(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    r = complaint(session, csrf, token, 'QA-F11 La puerta trasera no cierra bien en la parada.')
    check(r.status_code == 303 and 'c=0' in r.headers.get('Location', ''), 'HTTP %s %s' % (r.status_code, r.headers.get('Location')))
    STATE['complaints_accepted'] += 1
    return dict(obtenido='303 → %s' % r.headers['Location'], mensaje='Redirección a la página de gracias')


@case('F12', 'Funcional', 'Aceptar el secreto como parámetro de consulta (instalaciones antiguas)', 'POST ?secret=… sin cabecera',
      'HTTP 200 y 1 posición')
def f12(ctx):
    r = hook(position(device(12), iso(60), *MID), headers=HEADERS_JSON, query='?secret=' + SECRET)
    check(r.status_code == 200 and positions_of(ctx, 12) == 1, 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 200; 1 posición', mensaje='Sin cuerpo (200)')


# ================================================================================================
# Errors
# ================================================================================================
@case('E1', 'Error', 'Rechazar el webhook sin secreto', 'POST sin cabecera ni parámetro', 'HTTP 403 y 0 posiciones nuevas')
def e1(ctx):
    before = all_positions(ctx)
    r = hook(position(device(13), iso(60), *MID), headers=HEADERS_JSON)
    check(r.status_code == 403 and all_positions(ctx) == before, 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 403', mensaje='Respuesta vacía')


@case('E2', 'Error', 'Rechazar el webhook con un secreto equivocado', 'X-Webhook-Secret: incorrecto', 'HTTP 403')
def e2(ctx):
    r = hook(position(device(13), iso(60), *MID), headers={**HEADERS_JSON, 'X-Webhook-Secret': 'incorrecto'})
    check(r.status_code == 403, 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 403', mensaje='Respuesta vacía')


@case('E3', 'Error', 'Rechazar un cuerpo que no es JSON', 'Cuerpo "esto no es json"', 'HTTP 400, sin traza')
def e3(ctx):
    r = hook('esto no es json')
    check(r.status_code == 400 and not any(leak in r.text for leak in LEAKS), 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 400', mensaje='Respuesta vacía')


@case('E4', 'Error', 'Rechazar un método distinto de POST en el webhook', 'GET al webhook', 'HTTP 405 (o 404), nunca 200/500')
def e4(ctx):
    r = req('GET', WEBHOOK, headers={'X-Webhook-Secret': SECRET})
    check(r.status_code in (404, 405), 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP %s' % r.status_code, mensaje='Respuesta de método no permitido')


@case('E5', 'Error', 'Ignorar un JSON sin identificador de dispositivo', '{"foo": 1}', 'HTTP 200 y 0 posiciones nuevas')
def e5(ctx):
    before = all_positions(ctx)
    r = hook({'foo': 1})
    check(r.status_code == 200 and all_positions(ctx) == before, 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 200; nada guardado', mensaje='Sin cuerpo (200)')


@case('E6', 'Error', 'Ignorar una posición de un dispositivo desconocido', 'deviceId 999999', 'HTTP 200 y 0 posiciones nuevas')
def e6(ctx):
    before = all_positions(ctx)
    r = hook(position(999999, iso(60), *MID))
    check(r.status_code == 200 and all_positions(ctx) == before, 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 200; nada guardado', mensaje='Sin cuerpo (200)')


@case('E7', 'Error', 'No guardar una latitud fuera de rango', 'lat = 95° (el máximo es 90°)', 'Rechazo (4xx) o descarte; nunca 5xx ni dato guardado')
def e7(ctx):
    before = all_positions(ctx)
    r = hook(position(device(14), iso(60), 95.0, -78.62))
    check(r.status_code < 500, 'HTTP %s' % r.status_code)
    stored = all_positions(ctx) - before
    check(stored == 0, 'HTTP %s y se guardó la posición inválida (lat 95°)' % r.status_code)
    return dict(obtenido='HTTP %s; 0 guardadas' % r.status_code, mensaje='')


@case('E8', 'Error', 'Controlar una latitud no numérica', 'lat = "abc"', 'Rechazo (4xx) o descarte; nunca 5xx')
def e8(ctx):
    before = all_positions(ctx)
    r = hook(position(device(14), iso(61), 'abc', -78.62))
    check(r.status_code < 500, 'HTTP %s (error de servidor con latitud "abc")' % r.status_code)
    check(all_positions(ctx) == before, 'se guardó una posición inválida')
    return dict(obtenido='HTTP %s; 0 guardadas' % r.status_code, mensaje='')


@case('E9', 'Error', 'Controlar una hora GPS inválida', 'fixTime = "ayer"', 'Rechazo (4xx) o descarte; nunca 5xx')
def e9(ctx):
    r = hook(position(device(14), 'ayer', *MID))
    check(r.status_code < 500, 'HTTP %s (error de servidor con fixTime "ayer")' % r.status_code)
    return dict(obtenido='HTTP %s' % r.status_code, mensaje='')


@case('E10', 'Error', 'Responder 404 para una ruta pública inexistente', 'GET /rutas/NOPE y /rutas/NOPE/buses.json', 'HTTP 404 en ambas')
def e10(ctx):
    codes = (req('GET', BASE + '/rutas/NOPE').status_code, req('GET', BASE + '/rutas/NOPE/buses.json').status_code)
    check(codes == (404, 404), 'HTTP %s' % (codes,))
    return dict(obtenido='HTTP 404 / 404', mensaje='Página de no encontrado')


@case('E11', 'Error', 'No mostrar una ruta privada', 'GET /rutas/QA-PRIV y su feed', 'HTTP 404 en ambas')
def e11(ctx):
    codes = (req('GET', BASE + '/rutas/QA-PRIV').status_code, req('GET', BASE + '/rutas/QA-PRIV/buses.json').status_code)
    check(codes == (404, 404), 'HTTP %s' % (codes,))
    return dict(obtenido='HTTP 404 / 404', mensaje='Página de no encontrado')


@case('E12', 'Error', 'Rechazar una queja demasiado corta', 'description = "corto"', 'HTTP 400 con mensaje y 0 quejas nuevas')
def e12(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    before = complaint_count(ctx)
    r = complaint(session, csrf, token, 'corto')
    check(r.status_code == 400 and 'Escribe entre 10 y 2000 caracteres.' in r.text and complaint_count(ctx) == before,
          'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 400', mensaje='Escribe entre 10 y 2000 caracteres.')


@case('E13', 'Error', 'Rechazar un correo inválido', 'email = "no-es-correo"', 'HTTP 400 con mensaje y 0 quejas nuevas')
def e13(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    before = complaint_count(ctx)
    r = complaint(session, csrf, token, 'QA-E13 descripción suficientemente larga', email='no-es-correo')
    check(r.status_code == 400 and 'Ese correo no parece válido.' in r.text and complaint_count(ctx) == before,
          'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 400', mensaje='Ese correo no parece válido.')


@case('E14', 'Error', 'Rechazar un envío sin token CSRF', 'POST /quejas sin csrf_token', 'Rechazo 4xx y 0 quejas nuevas')
def e14(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    before = complaint_count(ctx)
    r = complaint(session, '', token, 'QA-E14 descripción suficientemente larga', csrf_token='')
    check(400 <= r.status_code < 500 and complaint_count(ctx) == before, 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP %s' % r.status_code, mensaje='Sesión expirada (CSRF inválido)')


@case('E15', 'Error', 'Descartar sin guardar un envío con el campo trampa lleno', 'website = "http://spam"',
      'Parece éxito (303) pero 0 quejas nuevas')
def e15(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    before = complaint_count(ctx)
    r = complaint(session, csrf, token, 'QA-E15 descripción suficientemente larga', website='http://spam')
    check(r.status_code == 303 and complaint_count(ctx) == before, 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 303; nada guardado', mensaje='Redirección a gracias sin folio')


@case('E16', 'Error', 'Descartar un envío demasiado rápido (menos de 3 s)', 'POST inmediato tras cargar el formulario',
      'Parece éxito (303) pero 0 quejas nuevas')
def e16(ctx):
    session = requests.Session()
    csrf, token = form(session)
    before = complaint_count(ctx)
    r = complaint(session, csrf, token, 'QA-E16 descripción suficientemente larga')
    check(r.status_code == 303 and complaint_count(ctx) == before, 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 303; nada guardado', mensaje='Redirección a gracias sin folio')


@case('E17', 'Error', 'Escapar lo que escribió la persona al volver a mostrar el formulario',
      'description con <script> y correo inválido', 'El HTML devuelto no contiene <script> sin escapar')
def e17(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    r = complaint(session, csrf, token, 'QA-E17 <script>alert(1)</script> texto largo', email='malo')
    check(r.status_code == 400, 'HTTP %s' % r.status_code)
    check('<script>alert(1)' not in r.text and '&lt;script&gt;alert(1)' in r.text, 'el texto no está escapado')
    return dict(obtenido='HTTP 400; &lt;script&gt; escapado', mensaje='Ese correo no parece válido.')


@case('E18', 'Error', 'Rechazar un cuerpo mayor de 20 KB', 'description de 25 000 caracteres', 'HTTP 413 y 0 quejas nuevas')
def e18(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    before = complaint_count(ctx)
    r = complaint(session, csrf, token, 'QA-E18 ' + 'x' * 25000)
    check(r.status_code == 413 and complaint_count(ctx) == before, 'HTTP %s' % r.status_code)
    return dict(obtenido='HTTP 413', mensaje='Respuesta vacía')


@case('E19', 'Error', 'Negar el mapa interno sin sesión', 'JSON-RPC a /bus_tracking/live sin sesión', 'Error de sesión; sin datos de buses')
def e19(ctx):
    r = req('POST', BASE + '/bus_tracking/live', json={'jsonrpc': '2.0', 'method': 'call', 'params': {}})
    body = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    check('result' not in body and ('error' in body or r.status_code in (401, 403)), 'HTTP %s %s' % (r.status_code, str(body)[:80]))
    return dict(obtenido='HTTP %s; %s' % (r.status_code, body.get('error', {}).get('data', {}).get('name', 'error')),
                mensaje=body.get('error', {}).get('data', {}).get('message', '')[:80])


@case('E20', 'Error', 'Negar el uso de notificaciones push a un usuario sin rol de administrador',
      'Usuario de solo lectura llama /bus_tracking/push/state', 'Error de acceso (AccessError)')
def e20(ctx):
    session = requests.Session()
    auth = session.post(BASE + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {
        'db': DB, 'login': 'qa_viewer', 'password': 'qa_viewer_pw'}}, timeout=30).json()
    check(auth.get('result', {}).get('uid'), 'no se pudo iniciar sesión con el usuario de solo lectura')
    r = req('POST', BASE + '/bus_tracking/push/state', json={'jsonrpc': '2.0', 'method': 'call', 'params': {}}, cookies=session.cookies)
    body = r.json()
    check('result' not in body and 'error' in body, 'respuesta: %s' % str(body)[:120])
    return dict(obtenido='AccessError', mensaje=body['error']['data'].get('message', '')[:80])


@case('E21', 'Error', 'Limitar el feed público a 60 peticiones por minuto y dirección',
      'Más de 60 GET seguidos a /rutas/QA1/buses.json', 'Aparece HTTP 429 con Retry-After')
def e21(ctx):
    time.sleep(61)                                   # let the one-minute window forget earlier hits
    codes = []
    retry = None
    for _ in range(70):
        r = req('GET', BASE + '/rutas/QA1/buses.json')
        codes.append(r.status_code)
        if r.status_code == 429:
            retry = r.headers.get('Retry-After')
            break
    check(429 in codes, 'nunca llegó el 429 en %d peticiones' % len(codes))
    check(codes.count(200) == 60 and retry, '200 antes del 429: %d; Retry-After=%s' % (codes.count(200), retry))
    return dict(obtenido='60 × HTTP 200 y luego 429 (Retry-After %s)' % retry, mensaje='')


@case('E22', 'Error', 'Limitar a 5 quejas por hora y dirección', 'Quejas válidas seguidas desde la misma dirección',
      'La sexta recibe HTTP 429 y no se guarda')
def e22(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    statuses = []
    for n in range(8):
        r = complaint(session, csrf, token, 'QA-E22 descripción número %d suficientemente larga' % n)
        statuses.append(r.status_code)
        if r.status_code == 429:
            break
    accepted_here = statuses.count(303)
    check(429 in statuses, 'nunca llegó el 429: %r' % statuses)
    check(STATE['complaints_accepted'] + accepted_here == 5, 'se aceptaron %d quejas en total (límite 5)' % (STATE['complaints_accepted'] + accepted_here))
    return dict(obtenido='5 aceptadas y la 6.ª con HTTP 429', mensaje='Enviaste varios reportes seguidos. Intenta de nuevo más tarde.')


# ================================================================================================
# Performance
# ================================================================================================
def timed_posts(items, workers):
    """items: list of payloads. Returns (durations, errors, wall seconds, status list)."""
    def one(payload):
        started = time.perf_counter()
        try:
            status = requests.post(WEBHOOK, data=json.dumps(payload), headers=HDR_SECRET, timeout=60).status_code
        except requests.RequestException:
            status = 0
        return time.perf_counter() - started, status

    wall = time.perf_counter()
    if workers == 1:
        outcomes = [one(item) for item in items]
    else:
        with futures.ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(one, items))
    wall = time.perf_counter() - wall
    return [o[0] for o in outcomes], [o[1] for o in outcomes], wall


@case('P1', 'Rendimiento', '100 posiciones secuenciales al webhook', '100 POST de un mismo bus, una hora GPS distinta cada uno',
      'Media < 0,5 s y 0 % de error')
def p1(ctx):
    items = [position(device(31), iso(3000 - i), -1.2650 + i * 1e-5, -78.6240, 5.0) for i in range(100)]
    times, statuses, wall = timed_posts(items, 1)
    stats = describe(times)
    errors = sum(1 for s in statuses if s != 200)
    _timings.extend(times)
    check(errors == 0 and stats['mean'] < 0.5, 'errores %d, media %.4f' % (errors, stats['mean']))
    return dict(obtenido='Media %.4f s; desv. %.4f; máx. %.4f; p95 %.4f' % (stats['mean'], stats['stdev'], stats['max'], stats['p95']),
                mensaje='100 × HTTP 200', stats=stats, errores=errors, rps=100 / wall)


@case('P2', 'Rendimiento', '200 posiciones con 20 hilos sobre 20 buses distintos', '20 hilos × 10 posiciones por bus',
      'Media < 1 s y error < 10 %')
def p2(ctx):
    items = [position(device(20 + b), iso(2500 - i), -1.2650 + i * 1e-5, -78.6240, 5.0) for b in range(1, 21) for i in range(10)]
    times, statuses, wall = timed_posts(items, 20)
    stats = describe(times)
    errors = sum(1 for s in statuses if s != 200)
    _timings.extend(times)
    check(errors / len(items) < 0.10 and stats['mean'] < 1.0, 'errores %d, media %.4f' % (errors, stats['mean']))
    return dict(obtenido='Media %.4f s; desv. %.4f; p95 %.4f; máx. %.4f; %d errores; %.1f req/s' % (
        stats['mean'], stats['stdev'], stats['p95'], stats['max'], errors, 200 / wall),
        mensaje='200 envíos', stats=stats, errores=errors, rps=200 / wall)


def timed_gets(url, count, workers=1):
    def one(_):
        started = time.perf_counter()
        status = requests.get(url, timeout=60).status_code
        return time.perf_counter() - started, status
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(one, range(count)))
    return [o[0] for o in outcomes], [o[1] for o in outcomes]


@case('P3', 'Rendimiento', '100 cargas de la página pública /rutas', '100 GET secuenciales', 'Media < 0,5 s y 0 % de error')
def p3(ctx):
    times, statuses = timed_gets(BASE + '/rutas', 100)
    stats = describe(times)
    errors = sum(1 for s in statuses if s != 200)
    _timings.extend(times)
    check(errors == 0 and stats['mean'] < 0.5, 'errores %d, media %.4f' % (errors, stats['mean']))
    return dict(obtenido='Media %.4f s; desv. %.4f; máx. %.4f' % (stats['mean'], stats['stdev'], stats['max']),
                mensaje='100 × HTTP 200', stats=stats, errores=errors)


@case('P4', 'Rendimiento', '45 lecturas del feed público (con caché de 5 s)', '45 GET a /rutas/QA1/buses.json', 'Media < 0,5 s y 0 % de error')
def p4(ctx):
    times, statuses = timed_gets(BASE + '/rutas/QA1/buses.json', 45)
    stats = describe(times)
    errors = sum(1 for s in statuses if s != 200)
    _timings.extend(times)
    check(errors == 0 and stats['mean'] < 0.5, 'errores %d, media %.4f' % (errors, stats['mean']))
    return dict(obtenido='Media %.4f s; desv. %.4f; máx. %.4f' % (stats['mean'], stats['stdev'], stats['max']),
                mensaje='45 × HTTP 200', stats=stats, errores=errors)


@case('P5', 'Rendimiento', '100 consultas al endpoint de salud', '100 GET a /bus_tracking/health', 'Media < 0,5 s y 0 % de error')
def p5(ctx):
    times, statuses = timed_gets(BASE + '/bus_tracking/health', 100)
    stats = describe(times)
    errors = sum(1 for s in statuses if s not in (200, 503))
    _timings.extend(times)
    check(errors == 0 and stats['mean'] < 0.5, 'errores %d, media %.4f' % (errors, stats['mean']))
    return dict(obtenido='Media %.4f s; desv. %.4f; máx. %.4f' % (stats['mean'], stats['stdev'], stats['max']),
                mensaje='HTTP %s' % sorted(set(statuses)), stats=stats, errores=errors)


@case('P6', 'Rendimiento', 'Integridad con 20 hilos que envían la misma posición a la vez', '20 POST idénticos simultáneos',
      '1 posición guardada y ningún HTTP 5xx')
def p6(ctx):
    payload = position(device(42), iso(90), -1.2650, -78.6245, 4.0)
    times, statuses, wall = timed_posts([payload] * 20, 20)
    _timings.extend(times)
    stored = positions_of(ctx, 42)
    stats = describe(times)
    check(stored == 1, 'posiciones guardadas: %d (estados %r)' % (stored, sorted(set(statuses))))
    check(not any(s >= 500 or s == 0 for s in statuses), 'hubo errores de servidor: %r' % sorted(set(statuses)))
    return dict(obtenido='1 guardada; estados %s; media %.4f s; p95 %.4f s' % (sorted(set(statuses)), stats['mean'], stats['p95']),
                mensaje='', stats=stats, errores=0)


@case('P7', 'Rendimiento', '60 posiciones distintas de un mismo bus con 20 hilos', '60 POST, un solo bus, 20 hilos',
      '60 guardadas, error < 10 % y p95 < 2 s')
def p7(ctx):
    items = [position(device(43), iso(2000 - i), -1.2650 + i * 1e-5, -78.6240, 5.0) for i in range(60)]
    times, statuses, wall = timed_posts(items, 20)
    _timings.extend(times)
    stored = positions_of(ctx, 43)
    stats = describe(times)
    errors = sum(1 for s in statuses if s != 200)
    check(errors / 60 < 0.10 and stats['p95'] < 2.0, 'errores %d, p95 %.4f, guardadas %d' % (errors, stats['p95'], stored))
    check(stored == 60 - errors, 'guardadas %d con %d errores' % (stored, errors))
    return dict(obtenido='%d guardadas; media %.4f s; p95 %.4f s; máx. %.4f s; %d errores' % (stored, stats['mean'], stats['p95'], stats['max'], errors),
                mensaje='', stats=stats, errores=errors, rps=60 / wall)


# ================================================================================================
# Usability
# ================================================================================================
@case('U1', 'Usabilidad', 'Mensajes de rechazo comprensibles y sin datos técnicos', '7 entradas inválidas hacia la persona usuaria',
      '100 % con mensaje de negocio, sin SQL ni trazas')
def u1(ctx):
    session = requests.Session()
    csrf, token = form(session)
    time.sleep(3.2)
    probes = [
        ('descripción corta', complaint(session, csrf, token, 'corto'), 'Escribe entre 10 y 2000 caracteres.'),
        ('correo inválido', complaint(session, csrf, token, 'QA-U1 descripción suficientemente larga', email='x'), 'Ese correo no parece válido.'),
        ('teléfono inválido', complaint(session, csrf, token, 'QA-U1 descripción suficientemente larga', phone='abc'), 'Ese teléfono no parece válido.'),
        ('descripción de 2 001 caracteres', complaint(session, csrf, token, 'QA-U1 ' + 'y' * 1996), 'Escribe entre 10 y 2000 caracteres.'),
        ('ruta inexistente', req('GET', BASE + '/rutas/NOPE'), None),
        ('webhook sin secreto', hook({'a': 1}, headers=HEADERS_JSON), None),
        ('cuerpo no JSON', hook('{{'), None),
    ]
    clear = 0
    detail = []
    for label, response, message in probes:
        leak = any(token_ in response.text for token_ in LEAKS)
        ok = not leak and (message is None or message in response.text) and response.status_code < 500
        clear += ok
        detail.append('%s: HTTP %s %s' % (label, response.status_code, 'claro' if ok else 'NO CLARO'))
    check(clear == len(probes), '%d de %d claros; %s' % (clear, len(probes), '; '.join(detail)))
    return dict(obtenido='%d/%d claros' % (clear, len(probes)), mensaje='; '.join(detail))


# ================================================================================================
def main():
    odoo = Odoo()
    prepare(odoo)
    ids = odoo.call('res.users', 'search', [('login', '=', 'qa_viewer')], context={'active_test': False})
    if ids:
        odoo.call('res.users', 'unlink', ids)
    group_user = odoo.call('ir.model.data', 'check_object_reference', 'bus_tracking', 'group_bus_user')[1]
    base_user = odoo.call('ir.model.data', 'check_object_reference', 'base', 'group_user')[1]
    odoo.call('res.users', 'create', [{'name': 'QA viewer', 'login': 'qa_viewer', 'password': 'qa_viewer_pw',
                                       'groups_id': [(6, 0, [base_user, group_user])]}])
    ctx = {'odoo': odoo}
    started = time.time()
    # E21 empties the one-minute window of the feed, so it goes last.
    ordered = [fn for fn in CASES if fn.meta['id'] != 'E21'] + [fn for fn in CASES if fn.meta['id'] == 'E21']
    for fn in ordered:
        run_case(fn, ctx)
    passed = sum(1 for r in RESULTS if r['estado'] == 'PASS')
    summary = {'fecha': time.strftime('%Y-%m-%d %H:%M:%S'), 'base': BASE, 'total': len(RESULTS), 'pass': passed,
               'fail': len(RESULTS) - passed, 'segundos': time.time() - started}
    path = save_json('suite.json', {'resumen': summary, 'casos': RESULTS})
    print('\n%d de %d PASS. Guardado en %s' % (passed, len(RESULTS), path))
    return 0 if passed == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
