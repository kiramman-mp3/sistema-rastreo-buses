"""Checks the Spanish translation of the module. Fails (exit 1) when es.po:

- has an entry with an empty msgstr, or
- names a model the module no longer defines (left over from a deleted model).

    python -X utf8 qa/traducciones.py

Only the standard library: it reads es.po and the module's models, Odoo is not needed.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
MODULE = os.path.join(ROOT, 'addons', 'bus_tracking')
PO = os.path.join(MODULE, 'i18n', 'es.po')


def entries(text):
    """(references, msgid, msgstr) per entry; the header (empty msgid) is skipped."""
    for block in re.split(r'\n\s*\n', text):
        refs = re.findall(r'^#[:.].*$', block, re.M)
        msgid = re.search(r'^msgid ((?:".*"\n?)+)', block, re.M)
        msgstr = re.search(r'^msgstr ((?:".*"\n?)+)', block, re.M)
        if not (msgid and msgstr):
            continue
        join = lambda m: ''.join(re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1)))  # noqa: E731
        if join(msgid):
            yield refs, join(msgid), join(msgstr)


def defined_models():
    names = set()
    for folder in ('models', 'wizard'):
        path = os.path.join(MODULE, folder)
        if not os.path.isdir(path):
            continue
        for name in os.listdir(path):
            if name.endswith('.py'):
                source = open(os.path.join(path, name), encoding='utf-8').read()
                names.update(re.findall(r"_name = '([\w.]+)'", source))
    return {name.replace('.', '_') for name in names}


def main():
    text = open(PO, encoding='utf-8').read()
    models = defined_models()
    empty, stale = [], set()
    for refs, msgid, msgstr in entries(text):
        if not msgstr:
            empty.append(msgid)
        for ref in refs:
            for model in re.findall(r'model:ir\.model(?:\.fields)?,\w+:bus_tracking\.(?:model|field)_(bus_\w+?)(?:__|\s|$)', ref):
                if model not in models:
                    stale.add(model)
    for msgid in empty:
        print('Sin traducir:', msgid[:80])
    for model in sorted(stale):
        print('Modelo que ya no existe:', model)
    print('es.po: %d sin traducir, %d modelos inexistentes' % (len(empty), len(stale)))
    return 1 if empty or stale else 0


if __name__ == '__main__':
    sys.exit(main())
