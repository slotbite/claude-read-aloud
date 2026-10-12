# exp-2 — Banco de voces: resultados

Fecha: 2026-10-12. Máquina: Windows 11, Python 3.12.10, RTX 5060 Laptop 8 GB, CPU de portátil.
Scripts en `bench/voces/`; los WAV y el `index.html` quedan fuera del repo, en
`%LOCALAPPDATA%\claude-read-aloud\bench\`. Todas las cifras son mediciones reales de esta
máquina (una pasada tras un calentamiento; 5 textos por voz). No se evaluó la calidad de las
voces: eso lo decide el oído de quien vote en el `index.html`.

## Resumen por modelo

| Modelo | Disp. | Tamaño | Carga | RTF medio | 1.er audio* | VRAM pico | Licencia |
|---|---|---|---|---|---|---|---|
| Kokoro-82M (ONNX) | CPU | 354 MB | 0,84 s | 0,38 | 1,1 s | — | Apache-2.0 |
| Supertonic-3 (ONNX) | CPU | 404 MB | 0,88 s | 0,35 | 1,4 s | — | MIT / OpenRAIL-M |
| Pocket TTS (torch CPU) | CPU | 238 MB | 1,2 s | 0,48 | no medido | — | MIT / CC-BY-4.0 |
| OmniVoice (fp16) | CUDA | 3,27 GB | 4,6 s | 0,27 | no medido | 2,5 GB | Apache-2.0 / CC-BY-NC |

\* Tiempo de sintetizar solo la primera oración de t1, sin streaming. Objetivo del plan: < 1 s.
Ninguno lo cumple por poco (Kokoro lo roza). RTF = síntesis / duración del audio (menor es mejor).

## Por voz

| Modelo / voz | RTF medio | t1 (s) | t4 largo (s) | t5 corto (s) | Audio t4 |
|---|---|---|---|---|---|
| kokoro / ef_dora | 0,38 | 3,4 | 9,5 | 0,53 | 26,3 s |
| kokoro / em_alex | 0,38 | 3,5 | 9,5 | 0,52 | 26,3 s |
| supertonic / F1 | 0,34 | 3,5 | 9,7 | 0,80 | 32,5 s |
| supertonic / M1 | 0,35 | 3,9 | 9,8 | 0,81 | 32,5 s |
| pocket / preset_alba | 0,48 | 4,1 | 12,3 | 0,84 | 26,2 s |
| pocket / preset_lola | 0,47 | 5,4 | 12,7 | 0,79 | 27,0 s |
| pocket / preset_rafael | 0,48 | 4,8 | 6,3 | 0,72 | 13,0 s (ver anomalías) |
| omnivoice / auto | 0,27 | 1,6 | 2,1 | 1,27 | 26,7 s |
| omnivoice / clon_ef_dora | 0,38 | 1,2 | 2,6 | 1,61 | 25,5 s |

Los tiempos completos por voz y texto están en `resultados.json` (regenerable).

## Lectura rápida

- En CPU, Kokoro y Supertonic rinden parecido (RTF ~0,35): una respuesta corta de 9 s de audio
  tarda ~3,5 s en sintetizarse completa, así que hay que sintetizar por oraciones y reproducir
  mientras se genera para bajar la latencia percibida.
- OmniVoice en GPU es el más rápido en textos largos (2 s para 27 s de audio) pero tiene un piso
  de ~1,3 s incluso para "Listo, ya quedó."; usa 2,5 GB de VRAM, pesa 3,3 GB y sus pesos son
  no comerciales. El prompt de clonación se calcula una vez (17 s la primera vez).
- Pocket TTS es el más lento de los CPU (RTF 0,48) y su clonación no pudo probarse (ver abajo).

## Qué falló y por qué

- **Pocket TTS, clonación (`clon_ef_dora`)**: no se pudo probar. Error exacto:
  `ValueError: We could not download the weights for the model with voice cloning, but you're
  trying to use voice cloning. [...] If you want access to the model with voice cloning, go to
  https://huggingface.co/kyutai/pocket-tts and accept the terms, then make sure you're logged
  in locally with `uvx hf auth login`.` Sin token no se pidió ninguna credencial. Sin
  clonación, `load_model(language="spanish")` descarga sin login y trae un catálogo de voces
  predefinidas; se probaron `lola`, `rafael` y `alba`. Verificado después en
  `pocket_tts/default_parameters.py` y `utils/utils.py`: `lola` es la voz por defecto de
  español (grabación de Common Voice `es`), **`rafael` es la de portugués** y `alba` la de
  inglés. Solo `lola` es nativa de español; las otras dos leen español con otro acento.
  **Acción del usuario si quiere probar la clonación**: aceptar los términos en
  https://huggingface.co/kyutai/pocket-tts, correr `hf auth login` (o `uvx hf auth login`) y
  repetir `run_pocket.py` (intenta `clon_ef_dora` primero).
- **Pocket en Windows**: `load_model` falla con `UnicodeDecodeError: 'charmap' codec can't
  decode byte 0x9d` al leer su YAML con la codificación por defecto; se resuelve ejecutando
  Python con `-X utf8` (`-I` ignora `PYTHONUTF8`).
- **Supertonic-3**: no hubo problema. El paquete de PyPI (`pip install supertonic`, 1.3.1) funciona
  directo y expone la misma API que el SDK del commit df0f968; se usó la instalación desde git
  en el banco y se comprobó aparte que PyPI instala la misma versión y firma.
  `auto_download` baja ~400 MB desde HF sin token.
- **OmniVoice**: sin problemas con torch 2.11+cu128 en Blackwell; no se instaló flash-attn.
  Avisa de que no encuentra ffmpeg (pydub), irrelevante para este uso.

## Anomalías y no verificado

- `pocket/preset_rafael/t4` dura 13,0 s frente a ~26 s del resto de voces: probable truncado o
  texto omitido (se usó `max_tokens=400`). Revisar de oído antes de descartar o ajustar.
- El "primer audio" no usa streaming; Pocket expone `generate_audio_stream`, no medido.
- Calidad, naturalidad y pronunciación de tecnicismos (t2) y cifras (t3) no evaluadas por mí.
- Las mediciones de CPU pueden variar con la carga del equipo; se repitieron Kokoro y Supertonic
  con el equipo en reposo y dieron lo mismo (±3 %).
- Tamaño de Supertonic/OmniVoice/Pocket = carpeta de descarga local (HF_HOME o `model_dir`).

## Regenerar

Ver `bench/voces/setup.md`. En resumen, tras instalar los venvs, ejecutar desde `bench\voces`
`run_kokoro.py`, `run_supertonic.py`, `run_pocket.py` (con `-X utf8`), `run_omnivoice.py` y
`python build_index.py`.
