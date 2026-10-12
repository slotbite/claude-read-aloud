# Changelog

## [Sin publicar]

### En curso
- Banco de voces en español (Kokoro, Pocket TTS, OmniVoice y otros) con página local para
  comparar — ver `docs/plan.md`.
- Cola de reproducción por sesión para que dos proyectos no hablen a la vez.

### Agregado
- (WIP) Aislamiento de archivos PID/WAV por sesión en `scripts/speak.py` (`--session`,
  `READ_ALOUD_SESSION`). Base de la cola por sesión; se completa en fix-3.

## 6af8da2 — feat: soporte para opencode y arreglo del audio con código omitido
## a98d88f — feat(kokoro): 54 voces, fonetización por idioma
## 3227000 — fix(windows): el hook ya no falla con el alias python3 de la Store
