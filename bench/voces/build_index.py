"""Une bench/res/*.json en bench/resultados.json y genera bench/index.html (sin servidor).
Uso: python bench\\voces\\build_index.py   (solo stdlib)"""
import json
from common import *

ORDEN = ["kokoro", "supertonic", "pocket", "omnivoice"]
res = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (BENCH / "res").glob("*.json")}
modelos = [res[m] for m in ORDEN if m in res] + [r for k, r in res.items() if k not in ORDEN]

for r in modelos:
    f = r["filas"]
    r["resumen"] = dict(
        rtf_medio=round(sum(x["rtf"] for x in f) / len(f), 3) if f else None,
        primer_audio_s=next(iter(sorted(x["primer_audio_s"] for x in f if x.get("primer_audio_s"))), None),
        vram_mb=max((x["vram_mb"] or 0 for x in f), default=0) or None,
        voces=sorted({x["voz"] for x in f}),
    )

datos = dict(
    textos={k: dict(nombre=v["nombre"], texto=v["texto"]) for k, v in DATA["textos"].items()},
    modelos=modelos)
(BENCH / "resultados.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")

plantilla = (HERE / "index.template.html").read_text(encoding="utf-8")
inline = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
(BENCH / "index.html").write_text(plantilla.replace("/*DATOS*/null", inline), encoding="utf-8")
print("ok:", BENCH / "index.html")
