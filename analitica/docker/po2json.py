"""Compila el .po de Superset a messages.mo (backend) y messages.json (Jed 1.x, frontend).

Las traducciones cuyos marcadores no coinciden con el original se descartan
(quedan en inglés) para que no truenen al formatear.
"""
import json
import os
import re
import sys

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

src, mo_dst, json_dst = sys.argv[1], sys.argv[2], sys.argv[3]
with open(src, "rb") as f:
    catalog = read_po(f)

# Terminología de CuboIP: "tablero" en lugar de "panel de control".
_TERMINOS = [
    (re.compile(r"\bpaneles de control\b"), "tableros"),
    (re.compile(r"\bPaneles de control\b"), "Tableros"),
    (re.compile(r"\bpanel de control\b"), "tablero"),
    (re.compile(r"\bPanel de control\b"), "Tablero"),
]


def _terminos(texto):
    for patron, nuevo in _TERMINOS:
        texto = patron.sub(nuevo, texto)
    return texto


for msg in catalog:
    if not msg.id:
        continue
    if isinstance(msg.string, (list, tuple)):
        msg.string = tuple(_terminos(s) for s in msg.string)
    elif msg.string:
        msg.string = _terminos(msg.string)

# Correcciones puntuales (cadenas vacías o marcadas como fuzzy en el .po oficial).
overrides_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "es_overrides.json")
if os.path.exists(overrides_path):
    with open(overrides_path, encoding="utf-8") as f:
        for msgid, texto in json.load(f).items():
            msg = catalog.get(msgid)
            if msg is None:
                catalog.add(msgid, texto)
            else:
                msg.string = texto
                msg.flags.discard("fuzzy")

descartadas = 0
for msg, errors in list(catalog.check()):
    if errors:
        msg.string = ("", "") if msg.pluralizable else ""
        descartadas += 1

with open(mo_dst, "wb") as f:
    write_mo(f, catalog, use_fuzzy=False)

messages = {
    "": {
        "domain": "superset",
        "plural_forms": catalog.plural_forms,
        "lang": str(catalog.locale),
    }
}
for msg in catalog:
    if not msg.id or msg.fuzzy:
        continue
    if isinstance(msg.id, (list, tuple)):
        key, values = msg.id[0], list(msg.string)
    else:
        key, values = msg.id, [msg.string]
    if not any(values):
        continue
    if msg.context:
        key = f"{msg.context}\u0004{key}"
    messages[key] = values

with open(json_dst, "w", encoding="utf-8") as f:
    json.dump({"domain": "superset", "locale_data": {"superset": messages}}, f, ensure_ascii=False)
print(f"{len(messages) - 1} cadenas traducidas, {descartadas} descartadas por marcadores")
