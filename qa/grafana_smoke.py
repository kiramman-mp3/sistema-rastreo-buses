"""Smoke test of a running Grafana (development or production). Standard library only.

    python qa/grafana_smoke.py                                  # http://localhost:3000, the development secrets
    GRAFANA_URL=https://grafana.example.com GRAFANA_ADMIN_PASSWORD=... GRAFANA_JWT_SECRET=... \
        python qa/grafana_smoke.py --frame-ancestor https://buses.example.com

It checks what must be true for the dashboards to be shown inside Odoo and for nothing else to get in:
health, the data source, the six dashboards, no anonymous access, the signed token (and not a forged or expired
one), a Viewer role, Explore off, sign-up off, and the headers that let only Odoo frame it.
Exit code 0 when everything passes, 1 otherwise.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request

DASHBOARDS = ['bus-resumen', 'bus-rutas', 'bus-puntualidad', 'bus-recorridos', 'bus-incidencias', 'bus-calidad']
DEV_SECRET = 'dev-grafana-jwt-secret-change-me'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def token(secret, role='Viewer', lifetime=300, issuer='odoo-bus-tracking'):
    head = b64(json.dumps({'alg': 'HS256', 'typ': 'JWT', 'kid': 'odoo'}).encode())
    now = int(time.time())
    body = b64(json.dumps({'iss': issuer, 'sub': 'odoo-smoke', 'role': role, 'iat': now - 10,
                           'exp': now + lifetime}).encode())
    return '%s.%s.%s' % (head, body, b64(hmac.new(secret.encode(), ('%s.%s' % (head, body)).encode(),
                                                  hashlib.sha256).digest()))


def get(url, headers=None, data=None):
    """(status, headers, body) without following redirects. With `data` (a dict) it is a JSON POST."""
    headers = dict(headers or {})
    if data is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(data).encode()
    request = urllib.request.Request(url, headers=headers, data=data)
    try:
        with OPENER.open(request, timeout=20) as response:
            return response.status, response.headers, response.read().decode('utf8', 'replace')
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read().decode('utf8', 'replace')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--url', default=os.environ.get('GRAFANA_URL', 'http://localhost:3000'))
    parser.add_argument('--admin-user', default='admin')
    parser.add_argument('--admin-password', default=os.environ.get('GRAFANA_ADMIN_PASSWORD', 'admin'))
    parser.add_argument('--secret', default=os.environ.get('GRAFANA_JWT_SECRET', DEV_SECRET))
    parser.add_argument('--frame-ancestor', default=None,
                        help='the address of Odoo: the only one allowed to frame Grafana (production, behind Caddy)')
    args = parser.parse_args()
    base = args.url.rstrip('/')
    admin = {'Authorization': 'Basic ' + base64.b64encode(
        ('%s:%s' % (args.admin_user, args.admin_password)).encode()).decode()}
    viewer = {'X-JWT-Assertion': token(args.secret)}
    results = []

    def check(name, ok, detail=''):
        results.append(ok)
        print(('PASS' if ok else 'FAIL'), name, ('- ' + detail) if detail and not ok else '')

    status, _h, body = get(base + '/api/health')
    check('Grafana is healthy', status == 200 and '"database": "ok"' in body.replace('":"', '": "'), 'HTTP %s' % status)

    status, _h, body = get(base + '/api/datasources/uid/bus-kpi/health', admin)
    message = ''
    try:
        message = json.loads(body).get('message', '')
    except ValueError:
        pass
    check('the data source reaches the database', status == 200 and 'ok' in message.lower(), '%s %s' % (status, message))

    status, _h, body = get(base + '/api/search?type=dash-db', admin)
    found = {d.get('uid') for d in json.loads(body)} if status == 200 else set()
    check('the six dashboards are loaded', set(DASHBOARDS) <= found, 'missing: %s' % sorted(set(DASHBOARDS) - found))

    status, _h, _b = get(base + '/api/user')
    check('anonymous access is refused', status in (401, 403), 'HTTP %s' % status)
    status, _h, _b = get(base + '/api/dashboards/uid/bus-resumen')
    check('a dashboard is not public', status in (401, 403), 'HTTP %s' % status)

    status, _h, body = get(base + '/api/user', viewer)
    check('a token signed by Odoo logs in', status == 200 and json.loads(body).get('login') == 'odoo-smoke', 'HTTP %s' % status)
    status, _h, body = get(base + '/api/user/orgs', viewer)
    roles = {o.get('role') for o in json.loads(body)} if status == 200 else set()
    check('the role is Viewer', roles == {'Viewer'}, str(roles))
    status, _h, _b = get(base + '/api/datasources', viewer, data={'name': 'x', 'type': 'prometheus', 'url': 'http://x',
                                                                  'access': 'proxy'})
    check('a Viewer cannot create data sources', status in (401, 403), 'HTTP %s' % status)

    def sql(text):
        query = {'queries': [{'refId': 'A', 'datasource': {'uid': 'bus-kpi'}, 'rawSql': text, 'format': 'table'}],
                 'from': 'now-1h', 'to': 'now'}
        return get(base + '/api/ds/query', viewer, data=query)
    status, _h, body = sql('SELECT COUNT(*) AS n FROM kpi_trips')
    check('a Viewer reads the kpi views', status == 200 and '"error"' not in body, 'HTTP %s' % status)
    # Grafana lets a Viewer write the SQL of a query by hand: what keeps the rest of Odoo out is the database role.
    for table in ('res_users', 'bus_position', 'ir_config_parameter'):
        status, _h, body = sql('SELECT * FROM %s LIMIT 1' % table)
        check('even by hand, a Viewer cannot read %s' % table, 'permission denied' in body, 'HTTP %s' % status)

    forged = token('a-different-secret-of-sixteen-plus')
    status, _h, _b = get(base + '/api/user', {'X-JWT-Assertion': forged})
    check('a token signed with another secret is refused', status in (401, 403), 'HTTP %s' % status)
    expired = token(args.secret, lifetime=-60)
    status, _h, _b = get(base + '/api/user', {'X-JWT-Assertion': expired})
    check('an expired token is refused', status in (401, 403), 'HTTP %s' % status)
    status, _h, _b = get(base + '/api/user', {'X-JWT-Assertion': token(args.secret, issuer='somebody-else')})
    check('a token from another issuer is refused', status in (401, 403), 'HTTP %s' % status)

    status, _h, _b = get(base + '/api/ds/query', viewer)
    check('queries need a body (no open endpoint)', status in (400, 401, 403, 404, 405), 'HTTP %s' % status)
    status, _h, _b = get(base + '/explore', viewer)
    check('Explore is off', status in (302, 403, 404), 'HTTP %s' % status)
    status, _h, _b = get(base + '/api/user/signup', data={'email': 'a@example.com', 'name': 'x', 'password': 'x'})
    check('sign-up is off', status in (401, 403, 404), 'HTTP %s' % status)

    status, headers, _b = get(base + '/d/bus-resumen?kiosk&auth_token=' + viewer['X-JWT-Assertion'])
    frame = (headers.get('X-Frame-Options') or '').upper()
    csp = headers.get('Content-Security-Policy') or ''
    if args.frame_ancestor:
        check('only Odoo can frame it', 'frame-ancestors %s' % args.frame_ancestor in csp and not frame,
              'X-Frame-Options=%r CSP=%r' % (frame, csp))
    else:
        check('it can be framed (embedding is allowed)', status == 200 and frame not in ('DENY', 'SAMEORIGIN'),
              'HTTP %s X-Frame-Options=%r' % (status, frame))

    passed = sum(results)
    print('\n%d of %d checks passed' % (passed, len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
