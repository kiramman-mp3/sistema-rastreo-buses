"""Errores humanos en la app del chofer (versión web): qué pasa si alguien toca dos veces, escribe mal la clave,
roza el SOS, pierde la señal a mitad del turno o cierra las alertas. 34 comprobaciones.

Mismos requisitos que `tablet_dispositivos.py`.

    python qa/tablet_errores_humanos.py [phone|tablet] [offline]

Al terminar con `offline` el turno queda abierto en el servidor (el cierre queda en cola sin red): ciérralo
antes de repetir (`python qa/tablet_datos_prueba.py` explica cómo).
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent / 'salida' / 'tablet'
OUT = HERE / 'errores_humanos'
OUT.mkdir(parents=True, exist_ok=True)
APP = 'http://localhost:8099'
SIZES = {'phone': (393, 852), 'tablet': (1180, 820)}
results = []


def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))
    print(('PASS ' if ok else 'FAIL ') + name + (f'  [{detail}]' if detail else ''), flush=True)


def text(page):
    return page.inner_text('body')


def has(page, pattern, timeout=0):
    if timeout:
        try:
            page.get_by_text(re.compile(pattern)).first.wait_for(state='visible', timeout=timeout)
        except Exception:
            return False
        return True
    return page.get_by_text(re.compile(pattern)).count() > 0


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else 'phone'
    w, h = SIZES[kind]
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--disable-web-security'])
        ctx = browser.new_context(viewport={'width': w, 'height': h}, has_touch=True, locale='es-EC',
                                  permissions=['geolocation'], geolocation={'latitude': -1.268, 'longitude': -78.6247})
        page = ctx.new_page()
        accept = {'v': True}
        page.on('dialog', lambda d: d.accept() if accept['v'] else d.dismiss())
        calls = []
        page.on('request', lambda r: calls.append(r.url) if '/bus_tracking/driver/' in r.url and r.method == 'POST' else None)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)[:160]))

        def count(path):
            return sum(1 for u in calls if u.endswith(path))

        # ------------------------------------------------------------------ login
        page.goto(APP, wait_until='networkidle', timeout=120000)
        page.wait_for_timeout(1500)
        disabled = page.evaluate("""() => { const b=[...document.querySelectorAll('[role=button]')].find(e => e.innerText.trim()==='Entrar');
            return b ? (b.getAttribute('aria-disabled')==='true' || b.hasAttribute('disabled')) : null; }""")
        check('login: "Entrar" is off while the fields are empty', disabled is True, str(disabled))

        page.get_by_placeholder('Usuario').fill('chofer1')
        page.get_by_placeholder('Contraseña').fill('mala-clave')
        page.keyboard.press('Enter')
        check('login: wrong password says so (Enter submits)', has(page, 'Usuario o clave incorrectos', 8000))
        check('login: the typed user is kept after the error', page.get_by_placeholder('Usuario').input_value() == 'chofer1')
        page.screenshot(path=str(OUT / f'{kind}-login-error.png'))

        # password reveal
        field = page.get_by_placeholder('Contraseña')
        before = field.get_attribute('type')
        page.get_by_text('Mostrar', exact=True).click()
        after = field.get_attribute('type')
        check('login: the Show button reveals the password', before == 'password' and after != 'password', f'{before}->{after}')
        page.get_by_text('Ocultar', exact=True).click()

        # no connection
        page.route('**/bus_tracking/driver/login', lambda r: r.abort())
        page.get_by_placeholder('Contraseña').fill('chofer1')
        page.get_by_text('Entrar', exact=True).click()
        check('login: no connection gives a clear message', has(page, 'Sin conexión', 6000))
        page.unroute('**/bus_tracking/driver/login')

        # language is remembered over a reload
        page.get_by_text('Kichwa', exact=True).click()
        page.reload(wait_until='networkidle')
        page.wait_for_timeout(1500)
        check('language: the choice (Kichwa) survives a reload', has(page, 'Pushakpa yaykuy'))
        page.get_by_text('Español', exact=True).click()
        page.wait_for_timeout(300)

        # good login, double tap on Enter button
        page.get_by_placeholder('Usuario').fill('chofer1')
        page.get_by_placeholder('Contraseña').fill('chofer1')
        n0 = count('/login')
        page.get_by_text('Entrar', exact=True).dblclick()
        page.wait_for_url('**/select', timeout=20000)
        check('login: a double tap sends one login', count('/login') - n0 == 1, str(count('/login') - n0))
        page.wait_for_timeout(2500)

        # ------------------------------------------------------------------ select
        # sign out: cancel keeps the session
        accept['v'] = False
        page.get_by_text('Cerrar sesión').first.click()
        page.wait_for_timeout(800)
        check('select: refusing "Cerrar sesión" keeps the driver in', '/select' in page.url)
        accept['v'] = True

        # start with a double click
        page.get_by_text('Bus 01').first.click()
        page.get_by_text(re.compile(r'^L1$')).first.click()
        n1 = count('/shift/start')
        page.get_by_text('Iniciar turno', exact=True).first.dblclick()
        page.wait_for_url('**/shift', timeout=20000)
        page.wait_for_timeout(5000)
        check('select: a double tap on "Iniciar turno" opens one shift', count('/shift/start') - n1 == 1, str(count('/shift/start') - n1))

        # ------------------------------------------------------------------ shift: alerts
        check('shift: two open alerts are announced', has(page, 'Parada larga') and (has(page, 'Fuera de ruta') or has(page, r'^\+1$')))
        close = page.get_by_text(re.compile(r'^Cerrar$'))
        check('shift: every alert has a "Cerrar" button', close.count() >= 1, str(close.count()))
        page.screenshot(path=str(OUT / f'{kind}-alerts-before.png'))
        close.first.click()
        page.wait_for_timeout(700)
        check('alerts: closing the first one removes it', not has(page, 'Parada larga'))
        check('alerts: the second one comes up', has(page, 'Fuera de ruta'))
        page.screenshot(path=str(OUT / f'{kind}-alerts-one-closed.png'))
        page.reload(wait_until='networkidle')
        page.wait_for_timeout(6000)
        check('alerts: after a reload the closed alert stays closed', not has(page, 'Parada larga') and has(page, 'Fuera de ruta'))
        page.get_by_text(re.compile(r'^Cerrar$')).first.click()
        page.wait_for_timeout(700)
        check('alerts: closing the last one leaves no alert', not has(page, 'Fuera de ruta') and not has(page, 'Parada larga'))
        page.wait_for_timeout(13000)     # the state is pulled again every 12 s: a closed alert must not come back
        check('alerts: they do not come back with the next refresh', not has(page, 'Fuera de ruta') and not has(page, 'Parada larga'))
        page.screenshot(path=str(OUT / f'{kind}-alerts-all-closed.png'))

        # ------------------------------------------------------------------ shift: SOS
        sos = page.get_by_text(re.compile(r'^SOS$')).first
        box = sos.bounding_box()
        cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        n2 = count('/incident')
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.wait_for_timeout(300)
        page.mouse.up()
        page.wait_for_timeout(1500)
        check('SOS: a short tap does NOT send an SOS', count('/incident') == n2 and not has(page, 'SOS enviado|Enviando SOS'))
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.wait_for_timeout(700)
        check('SOS: while holding it says "Sigue presionando"', has(page, 'Sigue presionando'))
        page.wait_for_timeout(1300)
        page.mouse.up()
        page.wait_for_timeout(2500)
        check('SOS: holding 1.5 s sends exactly one SOS', count('/incident') == n2 + 1, str(count('/incident') - n2))
        check('SOS: the driver is told it went out', has(page, r'SOS enviado|SOS guardado|La central vio'))
        page.screenshot(path=str(OUT / f'{kind}-sos-sent.png'))
        sos_close = page.get_by_text(re.compile(r'^Cerrar$'))
        check('SOS: once delivered its message can be closed', sos_close.count() >= 1)
        if sos_close.count():
            sos_close.first.click()
            page.wait_for_timeout(600)
            check('SOS: closing it removes the message', not has(page, r'SOS enviado|SOS guardado|La central vio'))

        # ------------------------------------------------------------------ shift: incident sheet
        page.get_by_text('Avisar un problema').first.click()
        page.wait_for_timeout(1500)
        send = lambda: page.get_by_text('Enviar aviso', exact=True)
        dis = page.evaluate("""() => { const b=[...document.querySelectorAll('[role=button]')].find(e => e.innerText.trim()==='Enviar aviso');
            return b ? (b.getAttribute('aria-disabled')==='true' || b.hasAttribute('disabled')) : null; }""")
        check('incident: "Enviar aviso" is off until a kind is chosen', dis is True, str(dis))
        check('incident: it says what to do', has(page, 'Elige qué pasa'))
        in_view = send().first.evaluate("e => { const r=e.getBoundingClientRect(); return r.bottom <= window.innerHeight + 1 && r.top >= 0; }")
        check('incident: the send button is always on screen', in_view)
        page.get_by_text('Tráfico', exact=True).first.click()
        page.get_by_placeholder(re.compile('trancón')).fill('Prueba automática: no es un aviso real')
        n3 = count('/incident')
        send().first.dblclick()
        page.wait_for_timeout(1200)
        check('incident: a double tap files one report', count('/incident') - n3 == 1, str(count('/incident') - n3))
        check('incident: the driver is told it was sent', has(page, 'Incidente enviado'))
        page.screenshot(path=str(OUT / f'{kind}-incident-sent.png'))
        page.wait_for_timeout(2600)
        check('incident: it goes back to the shift by itself', '/shift' in page.url, page.url)

        # ------------------------------------------------------------------ shift: signal lost mid-shift
        if 'offline' in sys.argv:
            ctx.set_offline(True)
            page.wait_for_timeout(16000)          # at least one refresh fails
            check('offline: the shift screen is still there (no crash, no white screen)', has(page, 'Próxima parada') and has(page, 'Terminar turno'))
            check('offline: the GPS state says it is saving, not "sending"', has(page, 'Sin red|Esperando|guardados'))
            page.screenshot(path=str(OUT / f'{kind}-offline.png'))
            page.get_by_text('Terminar turno').first.click()
            page.wait_for_timeout(3500)
            check('offline: the driver can still end the shift', '/select' in page.url, page.url)
            ctx.set_offline(False)
            page.wait_for_timeout(4000)

        # ------------------------------------------------------------------ shift: end
        if '/shift' in page.url:
            page.get_by_text('Terminar turno').first.click()
            page.wait_for_timeout(2500)
        check('end shift: it asked and ended (dialog accepted)', '/select' in page.url, page.url)
        # sign out for the next run
        page.get_by_text('Cerrar sesión').first.click()
        page.wait_for_timeout(2500)
        check('sign out: returns to the login', has(page, 'Ingreso del chofer', 6000))
        check('no script errors during the whole run', not errors, '; '.join(errors[:2]))
        browser.close()
    failed = [r for r in results if not r[1]]
    print(f'\n{len(results) - len(failed)} of {len(results)} checks passed')
    for name, _, detail in failed:
        print('  FAILED:', name, detail)


main()
