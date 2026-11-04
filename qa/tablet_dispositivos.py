"""Recorre la app del chofer (versión web) en 16 tamaños y orientaciones y avisa de lo que falte, quede
cortado o fuera de alcance: iPhone 16, Pixel Fold (pantalla exterior, interior y cuatro formas de pantalla
dividida), dos tabletas y dos teléfonos pequeños, cada uno de pie y acostado.

Requisitos (todo local, nunca producción):
  1. Odoo de desarrollo en http://localhost:8070 con los datos de `scripts/dev_seed.py` (chofer1/chofer1).
  2. En ese Odoo: la dirección del GPS en Ajustes (cualquier https://...) y alertas abiertas para «Bus 01»
     (`python qa/tablet_datos_prueba.py` imprime cómo prepararlas con `odoo shell`).
  3. La app web:  cd apps/conductor-tablet && EXPO_PUBLIC_ODOO_URL=http://localhost:8070 CI=1 npx expo start --web --port 8099

    python qa/tablet_dispositivos.py [nombre ...]      (sin nombres: todos)

Deja capturas en qa/salida/tablet/<dispositivo>/ y un resumen con lo que no se ve. Usa --disable-web-security
porque el Odoo de desarrollo no manda cabeceras CORS (la app nativa no las necesita).
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent / 'salida' / 'tablet'
OUT = HERE / 'capturas'
OUT.mkdir(parents=True, exist_ok=True)
APP = 'http://localhost:8099'

# CSS pixels. The folds are approximations of the Pixel Fold family (cover 411x923, inner ~791x820, 2.625 density).
DEVICES = {
    'iphone16-vertical': (393, 852, 3),
    'iphone16-horizontal': (852, 393, 3),
    'fold-exterior-vertical': (411, 923, 2.6),
    'fold-exterior-horizontal': (923, 411, 2.6),
    'fold-interior-vertical': (791, 820, 2.6),
    'fold-interior-horizontal': (820, 791, 2.6),
    'fold-split-vertical-a': (395, 820, 2.6),       # inner, two apps side by side
    'fold-split-vertical-b': (791, 410, 2.6),       # inner, two apps one above the other
    'fold-split-horizontal-a': (410, 791, 2.6),     # inner turned, two apps side by side
    'fold-split-horizontal-b': (820, 395, 2.6),     # inner turned, two apps one above the other
    'tablet-vertical': (820, 1180, 2),
    'tablet-horizontal': (1180, 820, 2),
    'tablet-android-vertical': (800, 1280, 2),
    'tablet-android-horizontal': (1280, 800, 2),
    'phone-small-vertical': (360, 640, 2),
    'phone-small-horizontal': (640, 360, 2),
}

# What must be on screen. (label, matcher). A matcher is a plain text (substring) or a regex.
LOGIN = [('title', 'Ingreso del chofer'), ('user', 'placeholder:Usuario'), ('password', 'placeholder:Contraseña'),
         ('enter', 'Entrar'), ('qr', 'Escanear credencial QR'), ('lang-es', 'Español'), ('lang-en', 'English'),
         ('lang-qu', 'Kichwa')]
SELECT = [('title', 'Elige tu bus y tu línea'), ('hello', 'Hola, Luis'), ('signout', 'Cerrar sesión'),
          ('bus-list', 'Elige el bus'), ('bus-01', 'Bus 01'), ('route-list', 'Elige la ruta'), ('L1', r're:^L1$'),
          ('start', 'Iniciar turno')]
STOPS = ['Campus Huachi', 'Mall de los Andes', 'Redondel de Huachi', 'Parque Cevallos']
SHIFT = [('bus', 'Bus 01'), ('mode', r're:^(Noche|Día)$'),
         ('clock', r're:^\d\d:\d\d$'), ('gps', r're:GPS|Sin red|Esperando'),
         ('alert-a', 'Parada larga'), ('alert-b', r're:Fuera de ruta|^\+1$'), ('close-alert', r're:^Cerrar$'),
         ('next-label', 'Próxima parada'), ('next-stop', 'Campus Huachi'), ('stops-left', r're:Quedan \d+ paradas|Última parada'),
         ('problem', 'Avisar un problema'), ('sos', r're:^SOS$'), ('end', 'Terminar turno')]

JS = """
(el) => {
  const r = el.getBoundingClientRect();
  const W = window.innerWidth, H = window.innerHeight;
  const out = {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y), notes: []};
  if (r.width === 0 || r.height === 0) { out.notes.push('empty'); return out; }
  if (r.left < -1 || r.top < -1 || r.right > W + 1 || r.bottom > H + 1) out.notes.push('outside-window');
  let p = el.parentElement;
  while (p && p !== document.body) {
    const cs = getComputedStyle(p);
    const clips = ['hidden', 'auto', 'scroll', 'clip'].includes(cs.overflowX) || ['hidden', 'auto', 'scroll', 'clip'].includes(cs.overflowY);
    if (clips) {
      const pr = p.getBoundingClientRect();
      if (r.left < pr.left - 1 || r.right > pr.right + 1 || r.top < pr.top - 1 || r.bottom > pr.bottom + 1) {
        const scrollable = p.scrollHeight > p.clientHeight + 2 || p.scrollWidth > p.clientWidth + 2;
        out.notes.push(scrollable ? 'needs-scroll' : 'clipped');
        break;
      }
    }
    p = p.parentElement;
  }
  const cx = Math.min(Math.max(r.x + r.width / 2, 0), W - 1), cy = Math.min(Math.max(r.y + r.height / 2, 0), H - 1);
  const top = document.elementFromPoint(cx, cy);
  if (top && !(el.contains(top) || top.contains(el))) out.notes.push('covered');
  return out;
}
"""


def locate(page, matcher):
    if matcher.startswith('placeholder:'):
        return page.get_by_placeholder(matcher.split(':', 1)[1])
    if matcher.startswith('re:'):
        return page.get_by_text(re.compile(matcher[3:]))
    return page.get_by_text(matcher, exact=False)


def probe(page, label, matcher):
    loc = locate(page, matcher)
    n = loc.count()
    if n == 0:
        return {'label': label, 'status': 'MISSING'}
    best = None
    for i in range(min(n, 6)):
        item = loc.nth(i)
        try:
            info = item.evaluate(JS)
        except Exception:
            continue
        if not info['notes'] and info['w'] > 0:
            return {'label': label, 'status': 'OK', 'w': info['w'], 'h': info['h']}
        if best is None or len(info['notes']) < len(best['notes']):
            best = info
    if best is None:
        return {'label': label, 'status': 'MISSING'}
    return {'label': label, 'status': ','.join(best['notes']) or 'EMPTY', 'w': best['w'], 'h': best['h']}


def page_overflow(page):
    return page.evaluate("""() => {
      const W = window.innerWidth;
      const bad = [...document.querySelectorAll('body *')].filter(e => {
        const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > W + 1 || r.left < -1);
      }).length;
      return {hscroll: document.documentElement.scrollWidth > W + 1, offscreen_elements: bad};
    }""")


def small_targets(page, minimum=44):
    """Interactive controls smaller than the touch minimum."""
    return page.evaluate("""(min) => [...document.querySelectorAll('button, [role=button], a, input, [tabindex="0"]')]
      .map(e => ({e, r: e.getBoundingClientRect()}))
      .filter(x => x.r.width > 0 && x.r.height > 0 && (x.r.height < min || x.r.width < min))
      .map(x => (x.e.innerText || x.e.getAttribute('aria-label') || x.e.getAttribute('placeholder') || x.e.tagName).slice(0, 30) + ' ' + Math.round(x.r.width) + 'x' + Math.round(x.r.height))
      .slice(0, 8)""", minimum)


def map_frame(page, wait=20):
    for _ in range(wait * 2):
        for f in page.frames:
            if f != page.main_frame:
                try:
                    if f.evaluate('() => !!window.busMap'):
                        return f
                except Exception:
                    pass
        page.wait_for_timeout(500)
    return None


def run_device(browser, name, spec, only_screens=None):
    w, h, scale = spec
    shots = OUT / name
    shots.mkdir(exist_ok=True)
    ctx = browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1, has_touch=True,
                              locale='es-EC', permissions=['geolocation'],
                              geolocation={'latitude': -1.2680, 'longitude': -78.6247})
    page = ctx.new_page()
    dialogs = []
    page.on('dialog', lambda d: (dialogs.append(d.message[:60]), d.accept()))
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)[:200]))
    report = {'device': name, 'size': f'{w}x{h}', 'screens': {}, 'errors': errors}

    def screen(key, items, extra=None):
        page.wait_for_timeout(700)
        rows = [probe(page, lab, m) for lab, m in items]
        if extra:
            rows += extra
        entry = {'problems': [r for r in rows if r['status'] != 'OK'], 'ok': sum(r['status'] == 'OK' for r in rows),
                 'overflow': page_overflow(page), 'small': small_targets(page)}
        report['screens'][key] = entry
        page.screenshot(path=str(shots / f'{key}.png'))

    page.goto(APP, wait_until='networkidle', timeout=120000)
    page.wait_for_timeout(1500)
    screen('1-login', LOGIN)

    page.get_by_placeholder('Usuario').fill('chofer1')
    page.get_by_placeholder('Contraseña').fill('chofer1')
    page.get_by_text('Entrar', exact=True).click()
    page.wait_for_url('**/select', timeout=20000)
    page.wait_for_timeout(2500)
    screen('2-select', SELECT)

    page.get_by_text('Bus 01').first.click()
    page.get_by_text(re.compile(r'^L1$')).first.click()
    page.wait_for_timeout(400)
    page.screenshot(path=str(shots / '2b-select-chosen.png'))
    try:
        page.get_by_text('Iniciar turno', exact=True).first.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass
    page.get_by_text('Iniciar turno', exact=True).first.click()
    page.wait_for_url('**/shift', timeout=20000)
    frame = map_frame(page)
    page.wait_for_timeout(5000)       # first GPS fix, state pulled
    stops = [(f'stop:{s}', s) for s in STOPS]
    extra = []
    extra.append({'label': 'map', 'status': 'OK' if frame else 'MISSING'})
    if frame:
        try:
            box = page.locator('iframe').first.evaluate(JS)
            extra.append({'label': 'map-size', 'status': 'OK' if not box['notes'] and box['h'] >= 56 and box['w'] >= 120 else ('small-or-' + ','.join(box['notes'])), 'w': box['w'], 'h': box['h']})
        except Exception as exc:
            extra.append({'label': 'map-size', 'status': 'ERR ' + str(exc)[:40]})
    screen('3-shift', SHIFT + stops, extra)
    shown = [r for r in report['screens']['3-shift']['problems'] if r['label'].startswith('stop:')]
    report['stops_visible'] = len(STOPS) - len(shown)

    # incident sheet
    page.get_by_text('Avisar un problema').first.click()
    page.wait_for_timeout(1500)
    screen('4-incident', [('title', r're:¿Qué pasa\?'), ('breakdown', 'Avería'), ('traffic', 'Tráfico'), ('accident', 'Accidente'),
                          ('send', 'Enviar aviso')])
    page.go_back()
    page.wait_for_timeout(1200)

    # GPS status
    page.get_by_text(re.compile(r'GPS|Sin red|Esperando')).first.click()
    page.wait_for_timeout(1500)
    screen('5-gps', [('title', 'Estado del GPS'), ('queue', 'Puntos en cola'), ('last', 'Último envío')])
    page.go_back()
    page.wait_for_timeout(1200)

    # end the shift through the confirmation
    page.get_by_text('Terminar turno').first.click()
    page.wait_for_timeout(3500)
    report['ended'] = '/select' in page.url
    report['dialogs'] = dialogs
    ctx.close()
    return report


def main():
    names = sys.argv[1:] or list(DEVICES)
    reports = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--disable-web-security'])
        for name in names:
            try:
                reports.append(run_device(browser, name, DEVICES[name]))
            except Exception as exc:
                reports.append({'device': name, 'fatal': str(exc)[:300]})
        browser.close()
    (HERE / 'report.json').write_text(json.dumps(reports, indent=1, ensure_ascii=False), encoding='utf8')
    for r in reports:
        if 'fatal' in r:
            print(f"\n## {r['device']}: FATAL {r['fatal']}")
            continue
        print(f"\n## {r['device']} {r['size']}  | stops visible {r.get('stops_visible')}/{len(STOPS)} | ended {r.get('ended')} | js errors {len(r['errors'])}")
        for key, s in r['screens'].items():
            flags = []
            if s['overflow']['hscroll'] or s['overflow']['offscreen_elements']:
                flags.append(f"overflow {s['overflow']}")
            if s['small']:
                flags.append('small ' + '; '.join(s['small'][:4]))
            probs = ', '.join(f"{p['label']}={p['status']}" for p in s['problems'])
            print(f"  {key}: ok {s['ok']}" + (f" | PROBLEMS: {probs}" if probs else '') + ''.join(f' | {f}' for f in flags))


main()
