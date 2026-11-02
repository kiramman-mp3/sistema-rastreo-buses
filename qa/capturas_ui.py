"""Screenshots of the public portal and the Odoo panel, for visual review.

    python qa/capturas_ui.py --base http://localhost:8070 --out <folder> [--only portal|panel] [--tag antes]

Needs `pip install playwright` and `python -m playwright install chromium`, and a database loaded with
`scripts/dev_seed.py`. Prints console errors per page so broken scripts show up next to the image.
"""
import argparse
import os
import sys

from playwright.sync_api import sync_playwright

PORTAL = [
    ('inicio', '/'),
    ('rutas', '/rutas'),
    ('ruta-L1', '/rutas/L1'),
    ('ruta-L4-vacia', '/rutas/L4'),
    ('quejas', '/quejas'),
    ('rutas-en', '/rutas?lang=en'),
]
PANEL = [
    ('login', '/web/login', False),
    ('mapa', '/web#action=bus_tracking.action_live_map', True),
    ('quejas', '/web#action=bus_tracking.action_bus_complaint', True),
    ('incidentes', '/web#action=bus_tracking.action_bus_incident', True),
]
SIZES = {'movil': (390, 844), 'escritorio': (1440, 900)}


def shoot(page, url, path, wait_ms, full=True, until='networkidle'):
    errors = []
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(url, wait_until=until)
    page.wait_for_timeout(wait_ms)
    if full:
        # Scroll like a person, so entrance animations and lazy pictures run before the full-page shot.
        page.evaluate("""async () => {
            const step = Math.round(window.innerHeight * 0.7);
            for (let y = 0; y < document.body.scrollHeight; y += step) {
                window.scrollTo(0, y);
                await new Promise((r) => setTimeout(r, 140));
            }
            window.scrollTo(0, 0);
        }""")
        page.wait_for_timeout(900)
    page.screenshot(path=path, full_page=full)
    print('%-45s %s' % (os.path.basename(path), 'OK' if not errors else 'ERRORES: %s' % errors[:3]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://localhost:8070')
    ap.add_argument('--out', required=True)
    ap.add_argument('--only', choices=['portal', 'panel'])
    ap.add_argument('--tag', default='')
    ap.add_argument('--pages', help='comma separated names to limit the run')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    wanted = set(args.pages.split(',')) if args.pages else None
    prefix = (args.tag + '-') if args.tag else ''
    with sync_playwright() as p:
        browser = p.chromium.launch()
        if args.only != 'panel':
            for size, (w, h) in SIZES.items():
                ctx = browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1,
                                          locale='es-EC', is_mobile=(size == 'movil'), has_touch=(size == 'movil'))
                for name, path in PORTAL:
                    if wanted and name not in wanted:
                        continue
                    shoot(ctx.new_page(), args.base + path,
                          os.path.join(args.out, '%sportal-%s-%s.png' % (prefix, name, size)), 2500)
                ctx.close()
        if args.only != 'portal':
            for size, (w, h) in (('escritorio', (1440, 900)), ('laptop', (1280, 720))):
                ctx = browser.new_context(viewport={'width': w, 'height': h}, locale='es-EC')
                page = ctx.new_page()
                for name, path, auth in PANEL:
                    if wanted and name not in wanted:
                        continue
                    if auth and '/web/login' in page.url or (auth and page.url == 'about:blank'):
                        page.goto(args.base + '/web/login')
                        page.fill('input[name=login]', 'admin')
                        page.fill('input[name=password]', 'admin')
                        page.click('button[type=submit]')
                        page.wait_for_load_state('load')
                    shoot(page, args.base + path,
                          os.path.join(args.out, '%spanel-%s-%s.png' % (prefix, name, size)), 4000, full=False, until='load')
                ctx.close()
        browser.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
