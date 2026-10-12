"""Utilidades compartidas por los scripts del banco de voces (stdlib; los runners aportan numpy/soundfile)."""
import json, os, pathlib, re, time

BENCH = pathlib.Path(os.environ.get("BENCH_DIR") or
                     pathlib.Path(os.environ["LOCALAPPDATA"]) / "claude-read-aloud" / "bench")
HERE = pathlib.Path(__file__).resolve().parent
DATA = json.loads((HERE / "textos.json").read_text(encoding="utf-8"))
TEXTOS = {k: v["texto"] for k, v in DATA["textos"].items()}
REF_TEXT = DATA["referencia"]["texto"]
REF_WAV = BENCH / "ref" / "ref_ef_dora.wav"
CLONES = BENCH / "ref" / "clones"  # lo llena importar_refs.py


def clones():
    """Referencias importadas: [(voz, wav, info)] con voz = "clon_<persona>"."""
    p = CLONES / "refs.json"
    if not p.exists():
        return []
    refs = json.loads(p.read_text(encoding="utf-8"))
    return [(f"clon_{k}", CLONES / f"{k}.wav", v) for k, v in refs.items()]


def primera_oracion(texto):
    return re.split(r"(?<=[.!?])\s+", texto, maxsplit=1)[0]


def dir_size_mb(*paths):
    total = 0
    for p in paths:
        p = pathlib.Path(p)
        files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
        total += sum(f.stat().st_size for f in files)
    return round(total / 1e6, 1)


def timed(fn):
    t = time.perf_counter()
    r = fn()
    return r, time.perf_counter() - t


class Recorder:
    """Acumula mediciones de un modelo y las guarda en bench/res/<modelo>.json."""

    def __init__(self, modelo, **meta):
        self.modelo = modelo
        self.meta = meta
        self.filas = []

    def wav(self, voz, tid):
        p = BENCH / "out" / self.modelo / voz / f"{tid}.wav"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def add(self, voz, tid, sintesis_s, duracion_s, dispositivo, vram_mb=None, **extra):
        self.filas.append(dict(
            voz=voz, texto=tid, sintesis_s=round(sintesis_s, 3),
            duracion_s=round(duracion_s, 3), rtf=round(sintesis_s / duracion_s, 3),
            dispositivo=dispositivo, vram_mb=vram_mb, **extra))
        print(f"{self.modelo}/{voz}/{tid}: sint={sintesis_s:.2f}s dur={duracion_s:.2f}s "
              f"rtf={sintesis_s / duracion_s:.2f}", flush=True)

    def save(self):
        out = BENCH / "res"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{self.modelo}.json").write_text(
            json.dumps(dict(modelo=self.modelo, meta=self.meta, filas=self.filas),
                       ensure_ascii=False, indent=1), encoding="utf-8")
