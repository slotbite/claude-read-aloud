"""OmniVoice (k2-fsa) en GPU fp16, sin FlashInfer ni flash-attn.
Voces: "auto" (sin referencia), "clon_ef_dora" (bench\\ref\\ref_ef_dora.wav + su texto) y
"clon_<persona>" (bench\\ref\\clones, ver importar_refs.py; Whisper transcribe la referencia).
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

# Referencias de importar_refs.py: sin transcripción, la hace Whisper (se guarda en refs.json
# para no repetirla). Una referencia que falla no corta el resto.
rec.meta["idiomas"], rec.meta["errores"] = {}, {}
refs_json = CLONES / "refs.json"
for voz, wav, info in clones():
    rec.meta["idiomas"][voz] = info["idioma"]
    try:
        if not info.get("texto"):
            if getattr(m, "_asr_pipe", None) is None:
                m.load_asr_model()  # whisper-large-v3-turbo, solo la primera vez
            onda, sr = sf.read(wav, dtype="float32")  # con ruta, Whisper exige ffmpeg
            info["texto"] = m.transcribe((onda, sr)).strip()
            refs = json.loads(refs_json.read_text(encoding="utf-8"))
            refs[voz.removeprefix("clon_")]["texto"] = info["texto"]
            refs_json.write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")
        VOCES[voz] = {"voice_clone_prompt": m.create_voice_clone_prompt(
            ref_audio=str(wav), ref_text=info.get("texto"))}
    except Exception as e:
        rec.meta["errores"][voz] = f"{type(e).__name__}: {e}"
        print("FALLO", voz, rec.meta["errores"][voz], flush=True)
m._asr_pipe = None  # libera Whisper para que no infle la VRAM medida
torch.cuda.empty_cache()


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
