"""Kokoro-82M (ONNX) con el venv que ya instaló el plugin. Voces: ef_dora, em_alex.
Uso: %LOCALAPPDATA%\\claude-read-aloud\\venv\\Scripts\\python.exe bench\\voces\\run_kokoro.py
También genera la referencia ef_dora (bench\\ref) que usan Pocket TTS y OmniVoice."""
import os, pathlib
import soundfile as sf
from kokoro_onnx import Kokoro
from common import *

D = pathlib.Path(os.environ["LOCALAPPDATA"]) / "claude-read-aloud" / "kokoro"
MODEL, VOICES = D / "kokoro-v1.0.onnx", D / "voices-v1.0.bin"

k, carga = timed(lambda: Kokoro(str(MODEL), str(VOICES)))
rec = Recorder("kokoro", carga_s=round(carga, 2), tamano_mb=dir_size_mb(MODEL, VOICES),
               dispositivo="cpu", licencia="Apache-2.0",
               nota="kokoro-onnx 0.6.1, onnxruntime CPU, lang=es")


def sint(texto, voz):
    return timed(lambda: k.create(texto, voice=voz, speed=1.0, lang="es"))


REF_WAV.parent.mkdir(parents=True, exist_ok=True)
(a, sr), _ = sint(REF_TEXT, "ef_dora")
sf.write(REF_WAV, a, sr)
print(f"referencia: {len(a) / sr:.1f}s -> {REF_WAV}")

for voz in ("ef_dora", "em_alex"):
    sint(TEXTOS["t5"], voz)  # calentamiento
    for tid, texto in TEXTOS.items():
        (a, sr), t = sint(texto, voz)
        sf.write(rec.wav(voz, tid), a, sr)
        extra = {}
        if tid == "t1":
            extra["primer_audio_s"] = round(sint(primera_oracion(texto), voz)[1], 3)
        rec.add(voz, tid, t, len(a) / sr, "cpu", **extra)
rec.save()
