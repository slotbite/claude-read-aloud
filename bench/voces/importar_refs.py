"""Importa referencias de clonación desde una carpeta procesada por voz-limpia.

Por cada persona (subcarpeta) elige el audio con más % de habla según informe.json y copia su
<nombre>_ref10s.wav a bench\\ref\\clones\\<persona>.wav. Escribe bench\\ref\\clones\\refs.json, que
leen run_pocket.py y run_omnivoice.py (voz "clon_<persona>").

Uso: python bench\\voces\\importar_refs.py C:\\ruta\\voces_limpia [--idioma persona=en ...]
     (idioma por defecto: es). Clona solo voces que tengas permiso de usar."""
import argparse, shutil
from common import *

ap = argparse.ArgumentParser()
ap.add_argument("limpia", type=pathlib.Path, help="carpeta de salida de voz-limpia")
ap.add_argument("--idioma", action="append", default=[], metavar="PERSONA=IDIOMA",
                help="idioma de la voz original si no es español (es, en, pt…)")
args = ap.parse_args()
idiomas = dict(x.split("=", 1) for x in args.idioma)

informe = json.loads((args.limpia / "informe.json").read_text(encoding="utf-8"))
mejor = {}
for rel, d in informe.items():
    persona = pathlib.PurePosixPath(rel).parts[0]
    if persona not in mejor or d["pct_habla"] > mejor[persona][1]["pct_habla"]:
        mejor[persona] = (rel, d)

CLONES.mkdir(parents=True, exist_ok=True)
refs = {}
for persona, (rel, d) in sorted(mejor.items()):
    src = (args.limpia / rel).with_name(pathlib.Path(rel).stem + "_ref10s.wav")
    shutil.copyfile(src, CLONES / f"{persona}.wav")
    refs[persona] = dict(origen=rel, idioma=idiomas.get(persona, "es"),
                         pct_habla=d["pct_habla"], ref_inicio_s=d.get("ref_inicio_s"))
    print(f"{persona:20} <- {rel} ({d['pct_habla']} % habla, {refs[persona]['idioma']})")

desconocidas = set(idiomas) - set(refs)
if desconocidas:
    print("AVISO: --idioma para personas que no están:", ", ".join(sorted(desconocidas)))
(CLONES / "refs.json").write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(refs)} referencias en {CLONES}")
