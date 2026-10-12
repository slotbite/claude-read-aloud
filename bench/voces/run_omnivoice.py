"""OmniVoice (k2-fsa) en GPU fp16, sin FlashInfer ni flash-attn.
Voces: "auto" (sin referencia) y "clon_ef_dora" (clona bench\\ref\\ref_ef_dora.wav + su texto).
El prompt de clonación se calcula una vez (su tiempo va en meta.prompt_clon_s).
Uso: bench\\venvs\\omnivoice\\Scripts\\python.exe bench\\voces\\run_omnivoice.py"""
import os
from common import *

os.environ["HF_HOME"] = str(BENCH / "models" / "hf-omnivoice")  # para poder medir el tamaño
import soundfile as sf, torch
from omnivoice import OmniVoice

(m), carga = timed(lambda: OmniVoice.from_pretrained(
    "k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16))
rec = Recorder("omnivoice", carga_s=round(carga, 2),
               tamano_mb=dir_size_mb(BENCH / "models" / "hf-omnivoice"), dispositivo="cuda",
               licencia="Apache-2.0 (código) / CC-BY-NC (pesos, no comercial)",
               nota="torch 2.11 cu128, fp16, num_step=16, omnivoice 0.2.1")
prompt, t_prompt = timed(lambda: m.create_voice_clone_prompt(
    ref_audio=str(REF_WAV), ref_text=REF_TEXT))
rec.meta["prompt_clon_s"] = round(t_prompt, 2)

VOCES = {"auto": {}, "clon_ef_dora": {"voice_clone_prompt": prompt}}


def sint(texto, kw):
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    a, t = timed(lambda: m.generate(text=texto, language="es", num_step=16, **kw))
    torch.cuda.synchronize()
    return a[0], t, round(torch.cuda.max_memory_allocated() / 1e6)


for voz, kw in VOCES.items():
    sint(TEXTOS["t5"], kw)  # calentamiento
    for tid, texto in TEXTOS.items():
        a, t, vram = sint(texto, kw)
        sf.write(rec.wav(voz, tid), a, 24000)
        rec.add(voz, tid, t, len(a) / 24000, "cuda", vram_mb=vram)
rec.save()
