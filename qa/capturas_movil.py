"""Screenshots of the driver app (Expo web build) at the four sizes it ships to, against the mock API.

    python qa/mock_driver_api.py --port 8090 &
    cd apps/conductor-tablet && EXPO_PUBLIC_ODOO_URL=http://localhost:8090 npx expo start --web --port 8082
    python qa/capturas_movil.py --out docs/calidad/evidencias/movil --tag base [--only shift] [--sizes phone-portrait]

Metro does not see edits on this project's path (it has an "o" with an accent): restart the dev
server before each run, or the pictures show old code.

Matrix: sizes x screens x day/night x scenario (see mock_driver_api.py). Each picture is also checked
for horizontal overflow; the run exits with 1 if any screen scrolls sideways or throws a page error.
"""
import argparse
import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

SIZES = {
    'phone-portrait': (390, 844),
    'phone-landscape': (844, 390),
    'tablet-portrait': (800, 1280),
    'tablet-landscape': (1280, 800),
}

# screen -> (route, needs an open shift)
SCREENS = {
    'login': ('login', None),
    'select': ('select', False),
    'shift': ('shift', True),
    'incident': ('incident', True),
    'gps': ('gps', True),
}

# (scenario, screens, extra state for the mock)
CASES = [
    ('normal', ['login', 'select', 'shift', 'incident', 'gps'], {'alert': False, 'sos': None}),
    ('worst', ['select', 'shift', 'incident'], {'alert': True, 'sos': 'seen'}),
    ('onestop', ['shift'], {'alert': False, 'sos': None}),
    ('empty', ['select'], {'alert': False, 'sos': None}),
    ('busy', ['select'], {'alert': False, 'sos': None}),
]


def mock(api, payload):
    request = urllib.request.Request(api + '/__scenario', data=json.dumps(payload).encode(), method='POST')
    urllib.request.urlopen(request, timeout=5).read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--tag', default='base')
    parser.add_argument('--web', default='http://localhost:8082')
    parser.add_argument('--api', default='http://localhost:8090')
    parser.add_argument('--only', nargs='*', help='screens to capture (default: all)')
    parser.add_argument('--sizes', nargs='*', default=list(SIZES))
    parser.add_argument('--modes', nargs='*', default=['day', 'night'])
    parser.add_argument('--scenarios', nargs='*', help='scenarios to capture (default: all)')
    args = parser.parse_args()

    folder = os.path.join(args.out, args.tag)
    os.makedirs(folder, exist_ok=True)
    problems = []
    taken = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for size in args.sizes:
            width, height = SIZES[size]
            for mode in args.modes:
                context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1)
                for scenario, screens, extra in CASES:
                    if args.scenarios and scenario not in args.scenarios:
                        continue
                    for screen in screens:
                        if args.only and screen not in args.only:
                            continue
                        route, shift = SCREENS[screen]
                        mock(args.api, {'scenario': scenario, 'open_shift': bool(shift), **extra})
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda e, errors=errors: errors.append(str(e)))
                        init = f"localStorage.setItem('uta.cabin.mode','{mode}');"
                        if screen != 'login':
                            init += f"localStorage.setItem('bus.driver.token','t');localStorage.setItem('bus.odoo.url','{args.api}');"
                        else:
                            init += f"localStorage.removeItem('bus.driver.token');localStorage.setItem('bus.odoo.url','{args.api}');"
                        page.add_init_script(init)
                        page.goto(f'{args.web}/{route}', wait_until='networkidle', timeout=120000)
                        page.wait_for_timeout(2500)
                        name = f'{scenario}-{screen}-{mode}-{size}'
                        page.screenshot(path=os.path.join(folder, name + '.png'))
                        sideways = page.evaluate('document.documentElement.scrollWidth > innerWidth')
                        taken += 1
                        if sideways or errors:
                            problems.append((name, 'sideways scroll' if sideways else errors[0][:120]))
                        page.close()
                context.close()
        browser.close()
    print(f'{taken} pictures in {folder}')
    for name, why in problems:
        print('PROBLEM', name, why)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
