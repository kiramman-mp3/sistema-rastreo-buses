"""A stand-in for the driver API of Odoo, to look at the tablet app without touching production.

    python qa/mock_driver_api.py [--port 8090] [--scenario normal] [--open-shift]

Point the app at it (it accepts plain http for addresses of the local network):

    web:      EXPO_PUBLIC_ODOO_URL=http://localhost:8090 npx expo start --web
    emulator: http://<LAN address of this PC>:8090 (long-press the Buses UTA mark on the login screen)

Every login works. Scenarios (also switchable while running, see below):

    normal  3 buses, 3 lines, 7 stops
    worst   long names, 9 buses (some taken or without GPS), 12 stops with long names, an off-route
            alert and an SOS the office has already seen: the realistic worst case for every field
    onestop a line with a single stop (the "last stop" wording)
    empty   no buses and no lines
    busy    every bus already taken

Switch while running:  POST /__scenario {"scenario": "worst", "open_shift": true, "sos": "seen",
                       "alert": true}   (every key is optional)   GET /__state shows the result.

The API sends no CORS headers in Odoo (the real app is not a browser); this one does, only for the
web preview. The alert detail follows the "lang" the app sends, like the Odoo API will after phase 33.
"""
import argparse
import json
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, content-type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
}

NORMAL = {
    'driver': 'Johan Rodríguez',
    'lines': [
        ('R1', 'Huachi – Ingahurco', '#7A1A22'),
        ('R2', 'Ficoa – Centro', '#1D6B44'),
        ('R3', 'Izamba – Parque Industrial', '#2255AA'),
    ],
    'buses': [('Bus 01', 'TBA-1001', True, True), ('Bus 02', 'TBA-1002', True, True), ('Bus 03', 'TBA-1003', False, True)],
    'stops': ['Campus Huachi', 'Mall de los Andes', 'Huachi Chico', 'Parque Cevallos', 'Mercado Central',
              'Campus Ingahurco', 'Terminal Terrestre'],
}
WORST = {
    'driver': 'Aleksandra Wiśniewska-Kowalczyk',
    'lines': [
        ('R1', 'Terminal Terrestre Ingahurco – Campus Huachi – Universidad Técnica de Ambato – Quinta Cadena', '#FFC62B'),
        ('Expreso U', 'Ficoa – Centro', '#3388FF'),
        ('R3', 'Izamba – Parque Industrial', '#2255AA'),
        ('R4', 'Huachi Chico – Atocha', '#FFFFFF'),
    ],
    'buses': [
        ('Bus articulado 12 (Expreso Universitario)', 'TBA-1001', True, True), ('Bus 02', 'TBA-1002', True, True),
        ('Bus 03', 'TBA-1003', False, True), ('Bus 04', 'TBA-1004', True, False), ('Bus 05', 'TBA-1005', True, True),
        ('Bus 06', 'TBA-1006', True, True), ('Bus 07', 'TBA-1007', False, True), ('Bus 08', 'TBA-1008', True, True),
        ('Jo', 'A-1', True, True),
    ],
    'stops': ['Terminal Terrestre Ingahurco – Andén 4', 'Av. Los Chasquis y Rodrigo Pachano', 'Campus Huachi UTA',
              'Mercado Mayorista', 'Parque Cevallos', 'Hospital Regional Docente Ambato', 'Plaza de Toros',
              'Quinta Cadena', 'Puente del Río Ambato', 'Redondel de Huachi Chico', 'Parada 11', 'Terminal Izamba'],
}
ONESTOP = {**NORMAL, 'stops': ['Campus Huachi']}
SCENARIOS = {
    'normal': NORMAL, 'worst': WORST, 'onestop': ONESTOP,
    'empty': {**NORMAL, 'lines': [], 'buses': []},
    'busy': {**NORMAL, 'buses': [(n, p, False, g) for n, p, _, g in NORMAL['buses']]},
}

STATE = {'scenario': 'normal', 'open_shift': False, 'sos': None, 'alert': False, 'vehicle': 1, 'route': 1}


def data():
    return SCENARIOS[STATE['scenario']]


def vehicles():
    d = data()
    return [{'id': i + 1, 'name': n, 'plate': p, 'route_id': 1 + (i % max(1, len(d['lines']))), 'available': a, 'has_gps': g}
            for i, (n, p, a, g) in enumerate(d['buses'])]


def routes():
    return [{'id': i + 1, 'code': c, 'name': n, 'color': col} for i, (c, n, col) in enumerate(data()['lines'])]


def shift():
    return {'id': 9, 'vehicle_id': STATE['vehicle'], 'route_id': STATE['route'], 'start': '2026-11-02T10:00:00Z'}


def me():
    return {'driver': {'id': 1, 'name': data()['driver']}, 'vehicles': vehicles(), 'routes': routes(),
            'shift': shift() if STATE['open_shift'] else None}


def alert_detail(lang):
    if lang == 'es':
        return 'Hasta 9 545 927 m fuera de su ruta (límite 150 m)'
    return 'Up to 9545927 m away from its route (limit 150 m)'


def state(lang):
    stops = data()['stops']
    sos = None
    if STATE['sos']:
        seen = STATE['sos'] == 'seen'
        sos = {'id': 1, 'sent_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'seen_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) if seen else None,
               'seen_by': 'Central UTA' if seen else None}
    alerts = []
    if STATE['alert']:
        alerts = [{'id': 1, 'kind': 'off_route', 'state': 'open', 'detail': alert_detail(lang), 'start': '2026-11-02T10:30:00Z'}]
    return {
        'shift': shift(), 'sos': sos, 'current_stop_id': None, 'next_stop_id': 1, 'direction': 'forward',
        'stops': [{'id': i + 1, 'name': n, 'sequence': i, 'arrived_at': None} for i, n in enumerate(stops)],
        'alerts': alerts,
    }


def route_map():
    d = data()
    stops = d['stops']
    pts = [[-1.24 + i * 0.004, -78.62 + i * 0.003] for i in range(len(stops))]
    code, name, color = d['lines'][STATE['route'] - 1] if d['lines'] else ('', '', '#7A1A22')
    return {
        'id': STATE['route'], 'code': code, 'name': name, 'color': color,
        'stops': [{'id': i + 1, 'name': n, 'sequence': i, 'lat': pts[i][0], 'lon': pts[i][1], 'radius': 40}
                  for i, n in enumerate(stops)],
        'lines': [{'name': 'ida', 'km': 5, 'points': pts}] if len(pts) > 1 else [],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = 'MockDriverApi'

    def log_message(self, *args):
        pass

    def _send(self, body, status=200):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        for key, value in CORS.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        for key, value in CORS.items():
            self.send_header(key, value)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/__state'):
            self._send(STATE)
        else:  # the OsmAnd position the tablet sends
            self._send({'ok': True})

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
        except ValueError:
            body = {}
        path = self.path.split('?')[0]
        if path == '/__scenario':
            if body.get('scenario') in SCENARIOS:
                STATE['scenario'] = body['scenario']
            for key in ('open_shift', 'sos', 'alert'):
                if key in body:
                    STATE[key] = body[key]
            return self._send(STATE)
        if path.endswith('/driver/login') or path.endswith('/driver/login_badge'):
            return self._send({'token': 'mock-token', 'driver': {'id': 1, 'name': data()['driver']}})
        if path.endswith('/driver/logout') or path.endswith('/driver/shift/end'):
            if path.endswith('/shift/end'):
                STATE['open_shift'] = False
            return self._send({'ok': True})
        if path.endswith('/driver/me'):
            return self._send(me())
        if path.endswith('/driver/shift/start'):
            STATE.update(open_shift=True, vehicle=int(body.get('vehicle_id') or 1), route=int(body.get('route_id') or 1))
            host = self.headers.get('Host', 'localhost')
            return self._send({'shift': shift(), 'traccar_unique_id': 'mock-1', 'gps_url': f'http://{host}/gps'})
        if path.endswith('/driver/state'):
            return self._send(state(body.get('lang') or 'en') if STATE['open_shift'] else {'error': 'no_shift'},
                              200 if STATE['open_shift'] else 409)
        if path.endswith('/driver/route'):
            return self._send(route_map())
        if path.endswith('/driver/incident'):
            if body.get('kind') == 'sos':
                STATE['sos'] = STATE['sos'] or 'sent'
            return self._send({'id': 1})
        self._send({'error': 'not_found'}, 404)


def lan_address():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(('10.255.255.255', 1))
        return probe.getsockname()[0]
    except OSError:
        return '127.0.0.1'
    finally:
        probe.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--port', type=int, default=8090)
    parser.add_argument('--scenario', choices=sorted(SCENARIOS), default='normal')
    parser.add_argument('--open-shift', action='store_true')
    args = parser.parse_args()
    STATE.update(scenario=args.scenario, open_shift=args.open_shift)
    print(f'Mock driver API: http://{lan_address()}:{args.port} (scenario {args.scenario})', flush=True)
    ThreadingHTTPServer(('0.0.0.0', args.port), Handler).serve_forever()
