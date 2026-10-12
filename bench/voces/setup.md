# Banco de voces: instalación y uso

Todo lo pesado vive fuera del repo, en `%LOCALAPPDATA%\claude-read-aloud\bench\`
(`venvs\<modelo>`, `models`, `ref`, `out`, `res`, `resultados.json`, `index.html`).
Un venv por modelo para evitar choques de torch/onnx. Requiere Windows, Python 3.12 y que el
plugin ya tenga Kokoro instalado (`/read-aloud:voice-setup`).

```powershell
$d = "$env:LOCALAPPDATA\claude-read-aloud"; $b = "$d\bench"
foreach ($m in "supertonic","pocket","omnivoice") { python -m venv "$b\venvs\$m" }

# Supertonic-3: el paquete de PyPI funciona directo (1.3.1). Alternativa fijada:
#   pip install "git+https://github.com/supertone-oss-archive/supertonic-py@df0f9686dac7fbbde391b759e2ee5286a3737622"
& "$b\venvs\supertonic\Scripts\python.exe" -m pip install supertonic soundfile

# Pocket TTS (torch CPU lo trae el paquete)
& "$b\venvs\pocket\Scripts\python.exe" -m pip install pocket-tts soundfile

# OmniVoice (GPU Blackwell: torch cu128 o superior; NO instalar flash-attn ni FlashInfer)
& "$b\venvs\omnivoice\Scripts\python.exe" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
& "$b\venvs\omnivoice\Scripts\python.exe" -m pip install omnivoice soundfile
```

## Generar y medir

Ejecutar desde la raíz del repo. Kokoro va primero porque crea la referencia `ref\ref_ef_dora.wav`
que usan Pocket y OmniVoice para clonar.

```powershell
$d = "$env:LOCALAPPDATA\claude-read-aloud"; $b = "$d\bench"; Set-Location bench\voces
& "$d\venv\Scripts\python.exe"            run_kokoro.py
& "$b\venvs\supertonic\Scripts\python.exe" run_supertonic.py
& "$b\venvs\pocket\Scripts\python.exe" -X utf8 run_pocket.py   # -X utf8 es obligatorio en Windows
& "$b\venvs\omnivoice\Scripts\python.exe"  run_omnivoice.py
python build_index.py                      # une res\*.json -> resultados.json + index.html
```

Abrir `%LOCALAPPDATA%\claude-read-aloud\bench\index.html` con doble clic.

## Notas

- Cada runner hace un calentamiento (texto t5) antes de medir. La carga del modelo se mide con
  los pesos ya descargados (la primera ejecución además descarga).
- "1.er audio" = tiempo de sintetizar solo la primera oración de t1 (ninguno de estos
  motores se usó en modo streaming).
- Los textos están en `textos.json`; la plantilla del HTML en `index.template.html`.
- **Pocket con clonación** exige aceptar los términos de `kyutai/pocket-tts` y
  `hf auth login` (ver `docs/voces/exp-2-resultados.md`). Con acceso, `run_pocket.py` ya
  intenta `clon_ef_dora` primero.
