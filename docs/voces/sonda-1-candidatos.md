# sonda-1 — Candidatos TTS en español

Fecha: 2026-10-12. Investigación de solo lectura; no se instaló nada. Fuentes: READMEs en
GitHub y Hugging Face, y la API de HF (`/api/models/<id>?blobs=true`) de `kyutai-labs/pocket-tts`,
`kyutai/pocket-tts`, `k2-fsa/OmniVoice`, `Supertone/supertonic-3` (ahora en
`supertone-oss-archive`) y `microsoft/VibeVoice` (`docs/vibevoice-realtime-0.5b.md`).
Lo que no está marcado como NO ENCONTRADO se verificó en esas fuentes.

Máquina objetivo: Windows 11, Python 3.12, RTX 5060 Laptop 8 GB (Blackwell sm_120: requiere
PyTorch con CUDA 12.8 o superior).

## Comparación

| | Pocket TTS | OmniVoice | Supertonic-3 | VibeVoice-Realtime |
|---|---|---|---|---|
| Español | Oficial (`spanish.yaml`, `spanish_24l.yaml`) | Sí (`es`, 27 559 h de entrenamiento) | Sí (`es`, 31 idiomas) | Experimental (oficial solo inglés) |
| Parámetros | ~100M | 612M (sobre Qwen3-0.6B) | ~99M (ONNX) | La API de HF reporta 1.02B en BF16 |
| Descarga | NO ENCONTRADO para español | ~3.3 GB | ~0.4 GB | ~2.0 GB |
| Ejecución | CPU nativo, 2 núcleos | Pensado para GPU (fp16); VRAM NO ENCONTRADO | CPU vía ONNX, sin torch | GPU (T4 / M4 Pro) |
| Latencia / RTF | ~200 ms al primer fragmento; ~6x tiempo real en M4 Air | RTF 0.09 en H100 fp16; sin datos para 8 GB | RTF 0.3 en un e-reader Boox | ~200–300 ms al primer audio |
| Instalación | `pip install pocket-tts` | torch cu128 + `pip install omnivoice`; flash-attn opcional | SDK desde el archivo (ver riesgos) | clonar el repo; recomienda flash-attn y Docker |
| Clonación | Sí, desde cualquier WAV | Sí, 3–10 s + transcripción | No (10 voces fijas) | No |
| Licencia código / pesos | MIT / CC-BY-4.0 | Apache-2.0 / **CC-BY-NC** | MIT / OpenRAIL-M | MIT / MIT, uso de investigación |
| Frecuencia de muestreo | `tts_model.sample_rate` (valor NO ENCONTRADO) | 24 kHz | 44.1 kHz | NO ENCONTRADO |

## Riesgos

- **Pocket TTS**: el repo de HF `kyutai/pocket-tts` tiene acceso restringido (*gated*):
  hay que iniciar sesión en HF y aceptar los términos. Existe una alternativa,
  `kyutai/pocket-tts-without-voice-cloning`. Sus voces predefinidas son inglesas, así que para
  español hay que clonar desde un WAV en español. El parámetro de idioma de la API de Python
  no está documentado; la CLI acepta `--language spanish`.
- **Supertonic-3**: el proyecto migró a `supertone-oss-archive` y el paquete de PyPI puede
  apuntar al espacio de nombres antiguo. Hay que instalar el SDK desde
  `supertone-oss-archive/supertonic-py` @ `df0f9686dac7fbbde391b759e2ee5286a3737622` con
  `model_dir` y `auto_download=False`.
- **OmniVoice**: los pesos son no comerciales. No se sabe cuánta VRAM usa ni qué RTF tiene en
  8 GB; hay que medirlo. No instalar FlashInfer.

## Código para generar un WAV (según los README)

```python
# Pocket TTS
from pocket_tts import TTSModel
import scipy.io.wavfile
m = TTSModel.load_model()
vs = m.get_state_for_audio_prompt("./voz_es.wav")
a = m.generate_audio(vs, "Hola mundo, esto es una prueba.")
scipy.io.wavfile.write("out.wav", m.sample_rate, a.numpy())
# CLI: pocket-tts generate --language spanish --voice ./voz_es.wav --text "Hola"
```

```python
# OmniVoice (para clonar se agregan ref_audio y ref_text)
from omnivoice import OmniVoice
import soundfile as sf, torch
model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16)
audio = model.generate(text="Hola, esto es una prueba.", num_step=16)
sf.write("out.wav", audio[0], 24000)
```

```python
# Supertonic-3 (voces fijas M1, ...)
from supertonic import TTS
tts = TTS(auto_download=True)
style = tts.get_voice_style(voice_name="M1")
wav, dur = tts.synthesize("Hola, esto es una prueba.", voice_style=style, lang="es")
tts.save_audio(wav, "out.wav")
```

## Decisión

Finalistas para el banco local (exp-2):

1. **Kokoro-82M**: línea base, ya integrado.
2. **Supertonic-3**: el más liviano, corre en CPU sin torch (evita el problema con Blackwell)
   y tiene español oficial.
3. **Pocket TTS**: corre en CPU, tiene clonación y español oficial.
4. **OmniVoice**: #2 del ranking en español y con clonación. Es el único que usa GPU.

**Descartados:**
- **VibeVoice-Realtime**: español experimental, la instalación recomendada pide flash-attn y
  Docker, y es solo para investigación.
- **VieNeu-TTS**: solo vietnamita.
- **El resto del top 11** (CosyVoice3, MOSS-TTS, Qwen3-TTS, VoxCPM2, IndexTTS-2.5, Magpie,
  fish s2-pro): no se revisaron por tener 1B parámetros o más. Quedan pendientes.

**Sin verificar:** VRAM de OmniVoice, RTF en CPU de Supertonic, frecuencia de muestreo de
Pocket y peso del modelo de Pocket en español.
