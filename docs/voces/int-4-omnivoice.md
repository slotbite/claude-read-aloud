# int-4: proveedor OmniVoice (clonación de voz)

Rama `feat/int-4-omnivoice`. Máquina de prueba: Windows 11, RTX 5060 Laptop 8 GB, torch 2.11.0+cu128,
omnivoice 0.2.1.

## Diseño

- `scripts/omnivoice_server.py` corre con el python del venv de OmniVoice. `http.server` stdlib en
  `127.0.0.1:<omnivoice_port>` (7853): `GET /health`, `POST /synth`, `POST /add-voice`,
  `POST /shutdown`. Una generación a la vez (lock). Cachea el `voice_clone_prompt` por voz y lo
  reconstruye si cambia `ref.wav` o `voz.json` (clave: mtime de ambos). Se apaga solo tras
  `omnivoice_idle_min` (15) minutos sin uso. Enlaza el puerto antes de cargar el modelo: un segundo
  servidor falla al instante (un servidor por máquina) y `/health` responde mientras carga.
- `speak.py` (proveedor `omnivoice`): `ov_ensure` consulta `/health`; si no responde lanza el
  servidor y espera hasta 150 s (muestra la cola del log si falla). Un POST por chunk; si el servidor
  se cae entre chunks (apagado por inactividad) lo reinicia una vez. El arranque ocurre antes de
  entrar a la cola, así que se calienta mientras la lectura espera turno.
- **Sobrevivir a `--stop`**: `kill_tree` usa `taskkill /T` (árbol por PID padre). El servidor se
  lanza vía un intermediario (`python -c`) que hace `Popen(DETACHED_PROCESS | NEW_PROCESS_GROUP |
  BREAKAWAY_FROM_JOB)` y termina; el servidor queda huérfano fuera del árbol. Breakaway evita
  también que el job del hook lo mate (si el job lo prohíbe se reintenta sin él).
- Biblioteca: `<data>/voces/<nombre>/ref.wav` (mono, 24 kHz, PCM16) + `voz.json`
  (`texto`, `idioma`, `origen` = nombre del archivo, no la ruta). Nombres `[A-Za-z0-9_-]{1,64}`.
  `cfg["voice"]` = nombre, `""` o `auto`. Una voz inexistente aborta con mensaje claro.
- Sin `--ref-text`, el servidor transcribe con Whisper large-v3-turbo pasando `(onda, sr)` (la ruta
  falla sin ffmpeg) y libera el ASR (`_asr_pipe = None` + `empty_cache`).
- Caché de modelos: `omnivoice_hf_cache` > si existe el hub del banco con el modelo, se usa como
  `HF_HUB_CACHE` (evita 3 GB) > caché HF por defecto. Solo `HF_HUB_CACHE`, nunca `HF_HOME`.
- `omnivoice_python` permite reutilizar un venv existente; `--setup omnivoice` crea
  `<data>/omnivoice-venv` (torch cu128 si hay `nvidia-smi`, si no CPU; `omnivoice`, `soundfile`) y
  pre-descarga el modelo. Sin CUDA el servidor usa CPU (float32) y speak.py lo avisa por stderr.
- Extras añadidos: `--render OUT.wav` (sintetiza sin reproducir ni cola), `--stop-server`,
  `--remove-voice`, env `READ_ALOUD_CONFIG` (config alternativa para pruebas), `load_config` tolera BOM.

## Mediciones (texto de 2 frases, ~5,7 s de audio, GPU sin competencia)

| Paso | Tiempo |
| --- | --- |
| 1.ª lectura (servidor frío: import torch + carga + prompt) | 20–22 s (hasta 30 s con disco/GPU ocupados) |
| 2.ª lectura (servidor caliente, mismo o distinto clon) | 1,3–1,5 s de pared (síntesis ~1,0–1,3 s) |
| Texto largo (6 repeticiones, ~35 s de audio) | 3,8 s |
| Texto de ~1.700 caracteres (varios chunks, `--render`) | ~11 s |
| `--add-voice` con `--ref-text` | ~0,2–0,3 s (servidor caliente) |
| `--add-voice` sin `--ref-text` (Whisper) | 14,6 s; transcripción correcta |
| Apagado por inactividad (`omnivoice_idle_min` 0,2 = 12 s) | servidor muerto a los 17 s |
| Reinicio automático tras apagado | 25 s (frío) |
| `--stop` con servidor vivo | 0,6 s; lector muerto, `/health` sigue respondiendo |

VRAM (`torch.cuda.memory_reserved` del servidor, expuesto en `/health` como `vram_mb`): sin
`empty_cache` tras cada síntesis quedaban **5,2 GB reservados** aunque el texto fuera corto; con
`empty_cache` quedan **~2,0 GB** en reposo. Whisper suma ~1,5 GB solo durante `--add-voice` sin texto.
Con el modelo cargado `nvidia-smi` marcó ~6,2 GB totales antes del cambio, ~0,7 GB sin servidor.

Aviso: la primera tanda de medidas (200 s / 177 s / 102 s por lectura) se hizo mientras el banco
(`bench/voces`) usaba la GPU a 100 %; se descartó. Las cifras de la tabla son con GPU libre.

## Pendiente / límites

- La 1.ª lectura tras 15 min de inactividad (o un reinicio) tarda ~20 s. Mitigación posible
  (no implementada): pre-calentar el servidor en el hook SessionStart.
- `--setup omnivoice` verificado solo en la rama "reutilizar `omnivoice_python`" + pre-descarga;
  la creación del venv propio con pip de torch (varios GB) no se ejecutó.
- Solo Windows probado; el lanzador POSIX (`start_new_session`) y CPU fallback no se probaron.
- `num_step` fijo en 16 (el servidor acepta `steps` por petición, sin clave de config aún).
