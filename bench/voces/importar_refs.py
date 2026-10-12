"""Importa referencias de clonación desde una carpeta procesada por voz-limpia.

Por cada persona (subcarpeta) elige el audio con más % de habla según informe.json y copia su
<nombre>_ref10s.wav a bench\\ref\\clones\\<persona>.wav. Escribe bench\\ref\\clones\\refs.json, que
leen run_pocket.py y run_omnivoice.py (voz "clon_<persona>").

Uso: python bench\\voces\\importar_refs.py C:\\ruta\\voces_limpia [--idioma persona=en ...]
     [--todas persona ...]   (todas sus referencias como <persona>_<id>, para elegir la mejor)
     (idioma por defecto: es). Clona solo voces que tengas permiso de usar."""
import argparse, shutil
from common import *

ap = argparse.ArgumentParser()
ap.add_argument("limpia", type=pathlib.Path, help="carpeta de salida de voz-limpia")
ap.add_argument("--idioma", action="append", default=[], metavar="PERSONA=IDIOMA",
                help="idioma de la voz original si no es español (es, en, pt…)")
ap.add_argument("--todas", action="append", default=[], metavar="PERSONA",
                help="importa todas las referencias de PERSONA, además de la mejor")
args = ap.parse_args()
idiomas = dict(x.split("=", 1) for x in args.idioma)

informe = json.loads((args.limpia / "informe.json").read_text(encoding="utf-8"))
elegidas = {}
for rel, d in informe.items():
    persona = pathlib.PurePosixPath(rel).parts[0]
    if persona not in elegidas or d["pct_habla"] > elegidas[persona][2]["pct_habla"]:
        elegidas[persona] = (persona, rel, d)
    if persona in args.todas:
        clave = f"{persona}_{pathlib.PurePosixPath(rel).stem.removeprefix(persona + '_')}"
        elegidas[clave] = (persona, rel, d)
# La mejor ya está como <persona>: no duplicarla entre las alternativas.
elegidas = {k: v for k, v in elegidas.items()
            if k == v[0] or v[1] != elegidas[v[0]][1]}

# Las transcripciones que hizo run_omnivoice.py se conservan si la referencia no cambió.
previas = json.loads((CLONES / "refs.json").read_text(encoding="utf-8")) \
    if (CLONES / "refs.json").exists() else {}
CLONES.mkdir(parents=True, exist_ok=True)
refs = {}
for clave, (persona, rel, d) in sorted(elegidas.items()):
    src = (args.limpia / rel).with_name(pathlib.Path(rel).stem + "_ref10s.wav")
    shutil.copyfile(src, CLONES / f"{clave}.wav")
    refs[clave] = dict(origen=rel, idioma=idiomas.get(persona, "es"),
                       pct_habla=d["pct_habla"], ref_inicio_s=d.get("ref_inicio_s"))
    if previas.get(clave, {}).get("origen") == rel and previas[clave].get("texto"):
        refs[clave]["texto"] = previas[clave]["texto"]
    print(f"{clave:28} <- {rel} ({d['pct_habla']} % habla, {refs[clave]['idioma']})")

desconocidas = (set(idiomas) | set(args.todas)) - {p for p, _, _ in elegidas.values()}
if desconocidas:
    print("AVISO: personas que no están:", ", ".join(sorted(desconocidas)))
(CLONES / "refs.json").write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(refs)} referencias en {CLONES}")
