"""Screenshots of the driver app in an Android emulator (LDPlayer or any adb device), walking the real flow.

    python qa/mock_driver_api.py --port 8090 &
    cd apps/conductor-tablet && EXPO_PUBLIC_ODOO_URL=http://<LAN address>:8090 \
        npx expo start --go --android --port 8083
    python qa/capturas_android.py --out docs/calidad/evidencias/movil --tag base \
        --expo exp://<LAN address>:8083 [--sizes phone-portrait] [--fonts 1.0 1.3 2.0]

For every size and font scale it logs in (any user works against the mock), picks a bus, starts a
shift, opens the problem sheet and the GPS status, ends the shift and signs out, taking a picture at
each screen. It never presses SOS. Size, density and font scale are restored at the end, also on error.

LDPlayer: Settings > Other settings > ADB debugging > "Open remote connection", then restart it. The
emulator is Android 9: it cannot judge vibration, predictive back or 120 Hz (use a real phone).
"""
import argparse
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ADB = os.environ.get('ADB', r'C:\LDPlayer\LDPlayer9\adb.exe')
SERIAL = os.environ.get('SERIAL', 'emulator-5554')

# name -> (size, density); the emulator's own screen is 1600x900 at 240 dpi (a tablet on its side)
SIZES = {
    'phone-portrait': ('1080x1920', '420'),
    'phone-landscape': ('1920x1080', '420'),
    'tablet-portrait': ('1600x1800', '320'),
    'tablet-landscape': ('1600x900', '240'),
}


def adb(*args, binary=False):
    result = subprocess.run([ADB, '-s', SERIAL, *args], capture_output=True, check=False)
    return result.stdout if binary else result.stdout.decode('utf-8', 'replace')


def ui_nodes():
    adb('shell', 'uiautomator', 'dump', '/sdcard/ui.xml')
    xml = adb('exec-out', 'cat', '/sdcard/ui.xml')
    start = xml.find('<?xml')
    if start < 0:
        return []
    return list(ET.fromstring(xml[start:]).iter('node'))


def center(node):
    left, top, right, bottom = map(int, re.findall(r'\d+', node.get('bounds')))
    return (left + right) // 2, (top + bottom) // 2


def find(*needles, clickable=False):
    """The first element whose text or description holds a needle (only clickable ones to tap)."""
    for node in ui_nodes():
        if clickable and node.get('clickable') != 'true':
            continue
        label = (node.get('text') or '') + '|' + (node.get('content-desc') or '')
        if any(n.lower() in label.lower() for n in needles):
            return node
    return None


def wait_for(*needles, seconds=20, clickable=False):
    end = time.time() + seconds
    while time.time() < end:
        node = find(*needles, clickable=clickable)
        if node is not None:
            return node
        time.sleep(1)
    raise RuntimeError('did not appear: ' + ' / '.join(needles))


def tap(*needles, seconds=20):
    node = wait_for(*needles, seconds=seconds, clickable=True)
    x, y = center(node)
    adb('shell', 'input', 'tap', str(x), str(y))


def type_into(label, text):
    tap(label)
    time.sleep(0.5)
    adb('shell', 'input', 'text', text)


def shot(folder, name):
    time.sleep(2.5)
    with open(os.path.join(folder, name + '.png'), 'wb') as handle:
        handle.write(adb('exec-out', 'screencap', '-p', binary=True))
    print('  ', name)


def walk(folder, prefix):
    """One pass through the app. Starts on the login screen, ends signed out."""
    wait_for('Ingresar manualmente', seconds=60)  # is Expo running and the app open?
    shot(folder, f'{prefix}-login')
    type_into('Usuario', 'chofer')
    type_into('Contraseña', 'clave')
    adb('shell', 'input', 'keyevent', '4')  # close the keyboard if there is one
    tap('Entrar')
    wait_for('Iniciar turno', 'Elige tu bus', 'Elige el bus', seconds=30)
    shot(folder, f'{prefix}-select')
    if find('Iniciar turno', clickable=True) is not None:
        tap('Iniciar turno')
        end = time.time() + 45
        while time.time() < end and find('Próxima parada') is None:
            button = find('Permitir', 'Allow', 'Mientras la app', 'While using', clickable=True)
            if button is not None:  # the location permission dialog, once or twice
                x, y = center(button)
                adb('shell', 'input', 'tap', str(x), str(y))
            time.sleep(1.5)
        wait_for('Próxima parada', seconds=10)
        shot(folder, f'{prefix}-shift')
        tap('Avisar un problema', 'Avisar')
        wait_for('Volver al turno', seconds=15)
        shot(folder, f'{prefix}-incident')
        tap('Volver al turno')
        wait_for('Terminar turno', seconds=15)
        tap('GPS enviando', 'Esperando señal', 'Sin red', 'GPS apagado', 'GPS')
        wait_for('Estado del GPS', seconds=15)
        shot(folder, f'{prefix}-gps')
        tap('Volver al turno')
        wait_for('Terminar turno', seconds=15)
        tap('Terminar turno')
        time.sleep(1.5)
        tap('TERMINAR TURNO', 'Terminar turno')  # the confirmation dialog repeats the label
        wait_for('Cerrar sesión', seconds=20)
    tap('Cerrar sesión')
    time.sleep(1.5)
    tap('CERRAR SESIÓN', 'Cerrar sesión')
    wait_for('Ingresar manualmente', 'Usuario', seconds=20)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--tag', default='base')
    parser.add_argument('--expo', required=True, help='exp://<LAN address>:8083')
    parser.add_argument('--sizes', nargs='*', default=list(SIZES))
    parser.add_argument('--fonts', nargs='*', default=['1.0'])
    parser.add_argument('--api', default='http://localhost:8090')
    args = parser.parse_args()

    folder = os.path.join(args.out, args.tag + '-android')
    os.makedirs(folder, exist_ok=True)
    if SERIAL not in adb('devices'):
        sys.exit(f'{SERIAL} is not connected: check the ADB setting of the emulator')
    url = args.expo + '?__expo_disable_fab=1&__expo_disable_auto_launch=1&__expo_disable_onboarding=1'
    # Expo Go keeps the last server address of the app: forget it so a saved production address can
    # never be used by this script (the app then falls back to EXPO_PUBLIC_ODOO_URL, the mock).
    adb('shell', 'pm', 'clear', 'host.exp.exponent')
    try:
        for size in args.sizes:
            screen, density = SIZES[size]
            for font in args.fonts:
                print(f'{size} font {font}')
                adb('shell', 'wm', 'size', screen)
                adb('shell', 'wm', 'density', density)
                adb('shell', 'settings', 'put', 'system', 'font_scale', font)
                adb('shell', 'am', 'force-stop', 'host.exp.exponent')
                time.sleep(2)
                adb('shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', f"'{url}'")
                try:
                    walk(folder, f'{size}-font{font}')
                except RuntimeError:
                    shot(folder, f'FAILED-{size}-font{font}')  # what was on screen when a wait ran out
                    raise
    finally:
        adb('shell', 'wm', 'size', 'reset')
        adb('shell', 'wm', 'density', 'reset')
        adb('shell', 'settings', 'delete', 'system', 'font_scale')
        print('emulator display and font scale restored')


if __name__ == '__main__':
    main()
