# Changelog

## [Sin publicar]

### En curso
- Banco de voces en español (Kokoro, Pocket TTS, OmniVoice y otros) con página local para
  comparar — ver `docs/plan.md`.

### Agregado
- Cola global FIFO de lecturas (fix-3): un solo audio a la vez en toda la máquina, con lock
  entre procesos (`O_EXCL` + recuperación de lock huérfano; PID vivo por `ctypes` en Windows).
  Lectura nueva de la misma sesión reemplaza a la suya; la de otra sesión espera (máx. 10 min).
- La sesión sale del `session_id` del hook Stop (`--session`, saneado); sin sesión se usa
  `manual`. WAV aislados por sesión. `speak-opencode.py` usa la sesión `opencode`.
- Opción `announce_project` (apagada por defecto): antepone el nombre de la carpeta del
  proyecto cuando cambia quien habla. Pruebas en `tests/test_queue.py`.

### Corregido
- Dos proyectos abiertos con auto-lectura ya no se cortan ni se superponen.
- `--stop` sin `--session` detiene lo que suena y vacía la cola; con `--session X`, solo X.
  En Windows ahora mata también el reproductor (`taskkill /T`).
- Se revierte el campo `env` del `hooks.json` (no verificado y la etiqueta fija no distinguía
  proyectos).

## 6af8da2 — feat: soporte para opencode y arreglo del audio con código omitido
## a98d88f — feat(kokoro): 54 voces, fonetización por idioma
## 3227000 — fix(windows): el hook ya no falla con el alias python3 de la Store
