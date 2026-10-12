"""Supertonic-3 (ONNX, CPU, sin torch). Voces F1 (mujer) y M1 (hombre), lang="es".
Uso: bench\\venvs\\supertonic\\Scripts\\python.exe bench\\voces\\run_supertonic.py"""
import soundfile as sf
from supertonic import TTS
from common import *

MODEL_DIR = BENCH / "models" / "supertonic-3"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

tts, carga = timed(lambda: TTS(model_dir=MODEL_DIR, auto_download=True))
# la primera ejecución incluye la descarga; se repite la carga para medir solo disco->memoria
tts, carga = timed(lambda: TTS(model_dir=MODEL_DIR, auto_download=False))
rec = Recorder("supertonic", carga_s=round(carga, 2), tamano_mb=dir_size_mb(MODEL_DIR),
               dispositivo="cpu", licencia="MIT (código) / OpenRAIL-M (pesos)",
               nota="supertonic-py 1.3.1 desde supertone-oss-archive @ df0f968, onnxruntime CPU")


def sint(texto, voz):
    st = tts.get_voice_style(voice_name=voz)
    (w, _), t = timed(lambda: tts.synthesize(texto, voice_style=st, lang="es"))
    return w, t


for voz in ("F1", "M1"):
    sint(TEXTOS["t5"], voz)  # calentamiento
    for tid, texto in TEXTOS.items():
        w, t = sint(texto, voz)
        p = rec.wav(voz, tid)
        tts.save_audio(w, str(p))
        extra = {}
        if tid == "t1":
            extra["primer_audio_s"] = round(sint(primera_oracion(texto), voz)[1], 3)
        rec.add(voz, tid, t, sf.info(str(p)).duration, "cpu", **extra)
rec.save()
