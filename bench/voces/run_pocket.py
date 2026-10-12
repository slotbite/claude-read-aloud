"""Pocket TTS (kyutai, ~100M, CPU) con language="spanish".
Voces: "clon_ef_dora" (clona bench\\ref\\ref_ef_dora.wav) y "preset_alba" (voz predefinida inglesa
hablando español). Cada voz se intenta por separado; los fallos quedan en meta.errores.
IMPORTANTE: ejecutar con -X utf8 (el paquete lee YAML con la codificación de Windows y falla).
Uso: bench\\venvs\\pocket\\Scripts\\python.exe -X utf8 bench\\voces\\run_pocket.py"""
import os
from common import *

os.environ["HF_HOME"] = str(BENCH / "models" / "hf-pocket")
import soundfile as sf
from pocket_tts import TTSModel

m, carga = timed(lambda: TTSModel.load_model(language="spanish"))
rec = Recorder("pocket", carga_s=round(carga, 2),
               tamano_mb=dir_size_mb(BENCH / "models" / "hf-pocket"), dispositivo="cpu",
               licencia="MIT (código) / CC-BY-4.0 (pesos)", errores={},
               nota="pocket-tts 3.3.0, torch 2.14.1 CPU, load_model(language='spanish')")
SR = m.sample_rate


def sint(estado, texto):
    a, t = timed(lambda: m.generate_audio(estado, texto, max_tokens=400))
    return a.squeeze().numpy(), t


def tanda(voz, fuente):
    try:
        estado = m.get_state_for_audio_prompt(fuente)
        sint(estado, TEXTOS["t5"])  # calentamiento
        for tid, texto in TEXTOS.items():
            a, t = sint(estado, texto)
            sf.write(rec.wav(voz, tid), a, SR)
            rec.add(voz, tid, t, len(a) / SR, "cpu")
    except Exception as e:
        rec.meta["errores"][voz] = f"{type(e).__name__}: {e}"
        print("FALLO", voz, rec.meta["errores"][voz], flush=True)


tanda("clon_ef_dora", str(REF_WAV))
tanda("preset_lola", "lola")      # el catálogo sugiere voces nativas por idioma
tanda("preset_rafael", "rafael")
tanda("preset_alba", "alba")      # voz inglesa leyendo español
rec.meta["tamano_mb"] = dir_size_mb(BENCH / "models" / "hf-pocket")
rec.save()
