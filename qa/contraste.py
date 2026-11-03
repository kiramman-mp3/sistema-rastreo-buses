"""Contrast of the design tokens (WCAG 2.x). Fails when a pair falls below its target.

    python qa/contraste.py

The pairs and targets are the ones documented in docs/DISENO.md: 7:1 (AAA) for body text on the
portal and the tablet, 4.5:1 (AA) for the rest of the text, 3:1 for large text and non-text marks.
"""
import sys

TOKENS = {
    'papel': '#F1F3F2', 'papel-2': '#E3E8E6', 'blanco': '#FFFFFF',
    'tinta': '#172025', 'tinta-2': '#3E4C51',
    'granate': '#7A1A22', 'granate-osc': '#5C1219',
    'senal': '#FFC62B',
    'ok': '#1D6B44', 'alerta': '#7A5000', 'peligro': '#A1221B',
    # tablet, night
    'noche': '#0E1316', 'noche-2': '#1A2226', 'noche-tinta': '#F2F5F4', 'noche-tinta-2': '#B9C4C2',
    'noche-ok': '#5FD19A', 'noche-alerta': '#FFC62B', 'noche-peligro': '#FF8A80',
}

PAIRS = [
    # (text, background, target, use)
    ('tinta', 'papel', 7.0, 'body text'),
    ('tinta', 'papel-2', 7.0, 'body text on panels'),
    ('tinta-2', 'papel', 7.0, 'secondary text'),
    ('tinta-2', 'papel-2', 7.0, 'secondary text on panels'),
    ('blanco', 'granate', 7.0, 'primary button'),
    ('blanco', 'granate-osc', 7.0, 'primary button pressed'),
    ('granate', 'papel', 7.0, 'links'),
    ('tinta', 'senal', 7.0, 'text on the signal yellow'),
    ('ok', 'papel', 4.5, 'moving status'),
    ('alerta', 'papel', 4.5, 'stopped status'),
    ('peligro', 'papel', 4.5, 'error text'),
    ('senal', 'tinta', 7.0, 'focus ring and live mark on ink'),
    ('noche-tinta', 'noche', 7.0, 'tablet night text'),
    ('noche-tinta-2', 'noche', 7.0, 'tablet night secondary'),
    ('noche-tinta', 'noche-2', 7.0, 'tablet night panels'),
    ('noche-ok', 'noche', 7.0, 'tablet night ok'),
    ('noche-alerta', 'noche', 7.0, 'tablet night warning'),
    ('noche-peligro', 'noche', 4.5, 'tablet night danger'),
    ('tinta', 'blanco', 7.0, 'tablet day text'),
    ('tinta-2', 'blanco', 7.0, 'tablet day secondary'),
]


def luminance(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# The route chip of the tablet is painted with a colour the office picks in Odoo, so its text is not a
# fixed token: the app chooses white or the dark ink (apps/conductor-tablet/src/ui/contrast.ts). Whatever
# the colour, the better of the two must reach 4:1 (a mid grey is the worst case, about 4.06:1); the
# listed colours are the ones the seed and the production lines use, which must reach 4.5:1.
ROUTE_CHIPS = ['#7A1A22', '#1E5560', '#9A4A12', '#3D4F8A', '#3388FF', '#FFC62B', '#FFFFFF']


def route_chip_failures():
    failures = []
    for value in range(0, 256, 5):
        grey = '#%02x%02x%02x' % (value, value, value)
        best = max(ratio(TOKENS['blanco'], grey), ratio(TOKENS['tinta'], grey))
        if best < 4.0:
            failures.append((grey, best, 4.0))
    for color in ROUTE_CHIPS:
        best = max(ratio(TOKENS['blanco'], color), ratio(TOKENS['tinta'], color))
        if best < 4.5:
            failures.append((color, best, 4.5))
    return failures


def main():
    failed = 0
    for fg, bg, target, use in PAIRS:
        r = ratio(TOKENS[fg], TOKENS[bg])
        ok = r >= target
        failed += not ok
        print('%-6s %5.2f:1 (min %.1f)  %-14s on %-12s %s' % ('OK' if ok else 'FALLA', r, target, fg, bg, use))
    chips = route_chip_failures()
    for color, best, target in chips:
        print('FALLA %5.2f:1 (min %.1f)  route chip %s: neither white nor the ink reads on it' % (best, target, color))
    failed += len(chips)
    if not chips:
        print('OK     route chips: white or ink reaches 4.5:1 on every line colour and 4:1 on any grey')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
