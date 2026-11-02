"""Screenshots of the driver tablet app running on the web build (Expo), against the local Odoo.

    cd apps/conductor-tablet && EXPO_PUBLIC_ODOO_URL=http://localhost:8070 npx expo start --web --port 8081
    python qa/capturas_tablet.py --out <folder> [--tag v1]

The driver API sends no CORS headers (the real app is not a browser), so this script relays the
calls to Odoo itself and adds them only here. The GPS cannot run in a browser: the last fix is
written into local storage the way the background task writes it on the tablet.
Needs a database loaded with scripts/dev_seed.py (chofer1 has an open shift; chofer2 has none).
"""
import argparse
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

ODOO = 'http://localhost:8070'
CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, content-type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
}


def relay(route):
    if route.request.method == 'OPTIONS':
        route.fulfill(status=204, headers=CORS)
        return
    response = route.fetch()
    headers = {**response.headers, **CORS}
    route.fulfill(status=response.status, headers=headers, body=response.body())


def gps_fix(page, speed_kmh, lat=-1.2600, lon=-78.6232, age_s=4):
    now = int(time.time() * 1000)
    sample = {'at': now - age_s * 1000, 'lat': lat, 'lon': lon, 'speedKmh': speed_kmh}
    sent = {'at': now - age_s * 1000, 'lat': lat, 'lon': lon, 'error': None}
    page.evaluate("""([sample, sent]) => {
        localStorage.setItem('uta.gps.sample', JSON.stringify(sample));
        localStorage.setItem('uta.gps.last', JSON.stringify(sent));
    }""", [sample, sent])


def shot(page, out, name, wait=1500):
    page.wait_for_timeout(wait)
    path = os.path.join(out, name + '.png')
    page.screenshot(path=path)
    print(name)


def sign_in(page, user, password):
    page.goto('http://localhost:8081/', wait_until='networkidle')
    page.wait_for_timeout(2500)
    page.get_by_placeholder('Usuario').fill(user)
    page.get_by_placeholder('Contraseña').fill(password)
    page.get_by_role('button', name='Entrar').click()
    page.wait_for_timeout(3500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--tag', default='')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    prefix = 'tablet-' + (args.tag + '-' if args.tag else '')
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for mode in ('day', 'night'):
            ctx = browser.new_context(viewport={'width': 1280, 'height': 800}, locale='es-EC', has_touch=True)
            ctx.route(ODOO + '/bus_tracking/**', relay)
            ctx.add_init_script('localStorage.setItem("uta.cabin.mode", %s)' % json.dumps(mode))
            page = ctx.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            if mode == 'day':
                page.goto('http://localhost:8081/', wait_until='networkidle')
                page.wait_for_timeout(2500)
                shot(page, args.out, prefix + 'login-dia')
            sign_in(page, 'chofer1', 'chofer1')
            gps_fix(page, 0)
            shot(page, args.out, prefix + 'turno-' + ('dia' if mode == 'day' else 'noche'), 6000)
            if mode == 'day':
                gps_fix(page, 42, age_s=7)
                shot(page, args.out, prefix + 'turno-en-marcha', 4000)
                gps_fix(page, 0)
                page.wait_for_timeout(3500)
                page.get_by_text('Avisar un problema', exact=True).click()
                page.get_by_role('radio', name='Tráfico').click()
                shot(page, args.out, prefix + 'incidente')
            ctx.unroute_all(behavior='ignoreErrors')
            ctx.close()
        ctx = browser.new_context(viewport={'width': 1280, 'height': 800}, locale='es-EC', has_touch=True)
        ctx.route(ODOO + '/bus_tracking/**', relay)
        ctx.add_init_script('localStorage.setItem("uta.cabin.mode", "day")')
        page = ctx.new_page()
        sign_in(page, 'chofer2', 'chofer2')
        shot(page, args.out, prefix + 'seleccion')
        ctx.unroute_all(behavior='ignoreErrors')
        ctx.close()
        browser.close()
    if errors:
        print('ERRORES:', errors[:5])
    return 0


if __name__ == '__main__':
    sys.exit(main())
