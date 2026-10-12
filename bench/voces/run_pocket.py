"""Pocket TTS (kyutai, ~100M, CPU) con language="spanish".
Voces: "clon_ef_dora" (clona bench\\ref\\ref_ef_dora.wav) y "preset_alba" (voz predefinida inglesa
hablando español). Cada voz se intenta por separado; los fallos quedan en meta.errores.
IMPORTANTE: ejecutar con -X utf8 (el paquete lee YAML con la codificación de Windows y falla).
Uso: bench\\venvs\\pocket\\Scripts\\python.exe -X utf8 bench\\voces\\run_pocket.py"""
import os
from common import *

# HF_HUB_CACHE y no HF_HOME: con HF_HOME el token de `hf auth login` queda fuera y
# Pocket cae sin aviso al modelo sin clonación.
os.environ["HF_HUB_CACHE"] = str(BENCH / "models" / "hf-pocket" / "hub")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
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


rec.meta["idiomas"] = {}
tanda("clon_ef_dora", str(REF_WAV))
for voz, wav, info in clones():   # referencias de importar_refs.py
    rec.meta["idiomas"][voz] = info["idioma"]
    tanda(voz, str(wav))
tanda("preset_lola", "lola")      # voz por defecto de español (Common Voice es)
tanda("preset_rafael", "rafael")  # voz por defecto de portugués, como contraste
tanda("preset_alba", "alba")      # voz inglesa leyendo español
rec.meta["tamano_mb"] = dir_size_mb(BENCH / "models" / "hf-pocket")
rec.save()
