# Changelog

## [Sin publicar]

### En curso
- Elegir voz en español escuchando el banco (`bench/voces/`) y, si hay ganador, integrarlo como
  proveedor (int-4) — ver `docs/plan.md`.

### Agregado
- Proveedor `omnivoice` (int-4, clonación de voz local): servidor persistente en loopback
  (`scripts/omnivoice_server.py`, se lanza solo, sobrevive a `--stop` y se apaga tras
  `omnivoice_idle_min` min sin uso), biblioteca de voces en `<data>/voces/` (`--add-voice`,
  `--remove-voice`, `--list-voices`; transcribe con Whisper si falta `--ref-text`),
  `--setup omnivoice`, `--render`, `--stop-server`. Mediciones en `docs/voces/int-4-omnivoice.md`.
- Cola global FIFO de lecturas (fix-3): un solo audio a la vez en toda la máquina, con lock
  entre procesos (`O_EXCL` + recuperación de lock huérfano; PID vivo por `ctypes` en Windows).
  Lectura nueva de la misma sesión reemplaza a la suya; la de otra sesión espera (máx. 10 min).
- La sesión sale del `session_id` del hook Stop (`--session`, saneado); sin sesión se usa
  `manual`. WAV aislados por sesión. `speak-opencode.py` usa la sesión `opencode`.
- Opción `announce_project` (apagada por defecto): antepone el nombre de la carpeta del
  proyecto cuando cambia quien habla. Pruebas en `tests/test_queue.py`.
- Banco de voces en `bench/voces/` (exp-2: Kokoro, Supertonic-3, Pocket TTS, OmniVoice): genera
  WAV con textos fijos, mide carga/RTF/VRAM y produce un `index.html` local para escuchar y
  votar. Resultados en `docs/voces/exp-2-resultados.md`; candidatos en
  `docs/voces/sonda-1-candidatos.md`.
- `bench/voces/importar_refs.py`: importa referencias limpias de voz-limpia como voces
  `clon_<persona>` para Pocket y OmniVoice; el index muestra las referencias originales.

### Corregido
- Pocket TTS no clonaba aunque hubiera `hf auth login`: el banco fijaba `HF_HOME` y el token
  quedaba fuera; ahora usa `HF_HUB_CACHE`.
- Dos proyectos abiertos con auto-lectura ya no se cortan ni se superponen.
- `--stop` sin `--session` detiene lo que suena y vacía la cola; con `--session X`, solo X.
  En Windows ahora mata también el reproductor (`taskkill /T`).
- Se revierte el campo `env` del `hooks.json` (no verificado y la etiqueta fija no distinguía
  proyectos).

## 6af8da2 — feat: soporte para opencode y arreglo del audio con código omitido
## a98d88f — feat(kokoro): 54 voces, fonetización por idioma
## 3227000 — fix(windows): el hook ya no falla con el alias python3 de la Store
