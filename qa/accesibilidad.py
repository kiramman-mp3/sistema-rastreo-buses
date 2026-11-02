"""Automatic accessibility check of the public site with axe-core (WCAG 2.1 A and AA rules).

    python qa/accesibilidad.py [--base http://localhost:8070] [--json salida.json]

Exits with 1 when any page has a violation. axe-core (MPL-2.0) is vendored in qa/recursos/axe.min.js.
It finds what a machine can find (contrast, names, landmarks, labels); it does not replace testing
with people and a screen reader (docs/calidad/12-validacion-ux.md).
"""
import argparse
import json
import os
import sys

from playwright.sync_api import sync_playwright

AXE = os.path.join(os.path.dirname(__file__), 'recursos', 'axe.min.js')
PAGES = ['/', '/rutas', '/rutas?q=huachi', '/rutas/L1', '/rutas/L4', '/quejas', '/rutas?lang=en']
SIZES = {'movil': (390, 844), 'escritorio': (1440, 900)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://localhost:8070')
    ap.add_argument('--json')
    args = ap.parse_args()
    results = {}
    total = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for size, (w, h) in SIZES.items():
            page = browser.new_page(viewport={'width': w, 'height': h})
            for path in PAGES:
                page.goto(args.base + path, wait_until='networkidle')
                page.wait_for_timeout(1200)
                # entrances only change opacity; show everything so axe measures the final colours
                page.evaluate("document.querySelectorAll('.entra').forEach(e => e.classList.add('visto'))")
                page.wait_for_timeout(700)
                page.add_script_tag(path=AXE)
                found = page.evaluate("""async () => {
                    const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}});
                    return r.violations.map(v => ({id: v.id, impact: v.impact, help: v.help,
                        nodes: v.nodes.slice(0, 3).map(n => n.target.join(' '))}));
                }""")
                results['%s %s' % (size, path)] = found
                total += len(found)
                print('%-34s %s' % ('%s %s' % (size, path), 'OK' if not found else '%d problemas' % len(found)))
                for v in found:
                    print('    - [%s] %s: %s  %s' % (v['impact'], v['id'], v['help'], v['nodes']))
            page.close()
        browser.close()
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
    print('TOTAL: %d problemas' % total)
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
