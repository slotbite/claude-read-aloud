# Plan — voces livianas en español + cola por sesión

Rama integradora: `feat/voces-y-cola-sesion` (base: `slotbite/main` @ 6af8da2).
Registro del lote: `.orquestacion/voces-cola/` (local, no versionado).

## Objetivos

1. **Elegir un TTS liviano y rápido para leer respuestas de chat en español**, comparando
   candidatos en una página HTML local, oyendo el mismo texto con cada uno.
2. **Que dos proyectos abiertos a la vez no se pisen al hablar**: cola de reproducción global
   con identificación por `session_id`.

## Criterios de selección de voces

- Español soportado oficialmente (los que no lo tienen se descartan sin probar: VieNeu-TTS).
- Corre local; preferible en CPU, aceptable en GPU de 8 GB (RTX 5060 Laptop, Blackwell).
- Latencia al primer audio baja (objetivo < 1 s en esta máquina) y RTF < 1.
- Instalable en Windows con Python 3.10–3.12 en un venv propio.
- Clonación de voz: deseable, no obligatoria.

## Candidatos

| Modelo | Por qué | Notas |
|---|---|---|
| Kokoro-82M | Ya integrado; #1 en Open TTS Leaderboard (español) | Línea base |
| Pocket TTS (kyutai) | 100M, CPU, ~200 ms primer audio, clonación, español | MIT |
| OmniVoice (k2-fsa) | #2 en el leaderboard español, clonación | Revisar tamaño/GPU |
| Supertonic-3 | #5, conocido por ser muy rápido | Revisar español |
| VibeVoice-Realtime-0.5B | Voces `sp-*` experimentales | Solo investigación, inglés primero |
| Otros del top 11 | Solo si son livianos | CosyVoice3, MOSS, Qwen3-TTS, VoxCPM2, IndexTTS, Magpie |

## Tareas

| ID | Qué | Tipo | Depende de | Entregable |
|---|---|---|---|---|
| sonda-1 | Investigar candidatos: español, tamaño, CPU/GPU, Windows, API, licencia | sonda (solo lectura) | — | `docs/voces/sonda-1-candidatos.md` |
| exp-2 | Banco local: instalar finalistas, generar WAV con textos fijos, medir latencia/RTF, `index.html` para escuchar y votar | ejecutor | sonda-1 | `bench/voces/` + `docs/voces/exp-2-resultados.md` |
| fix-3 | Cola de reproducción por `session_id` en `speak.py` | ejecutor | — | cambios en `scripts/`, `hooks/`, `skills/` |
| int-4 | Integrar el ganador como proveedor (si lo hay) | ejecutor | exp-2 + decisión del usuario | — |

## Diseño de fix-3 (cola por sesión)

- El hook de Claude Code recibe `session_id` en su JSON de entrada: esa es la identidad, no una
  etiqueta fija por herramienta (`"claude-code"` no distingue dos proyectos).
- Un solo audio a la vez en toda la máquina: lock global + cola FIFO en el directorio temporal.
- Una lectura nueva de la **misma** sesión reemplaza a la suya (en curso o en cola).
- Una lectura de **otra** sesión espera su turno; no interrumpe.
- `--stop` sin `--session` detiene todo y vacía la cola; con `--session` solo esa sesión.
- Se revierte el `env` agregado a `hooks/hooks.json` (no verificado como campo válido).

## Estado

- exp-2 hecho: banco en `bench/voces/`. En CPU Kokoro y Supertonic rinden RTF ~0,35 (primer audio
  1,1–1,4 s), Pocket 0,48 (clonación bloqueada por HF gated), OmniVoice en GPU 0,27 con 2,5 GB
  de VRAM. Detalle en `docs/voces/exp-2-resultados.md`.

Ver `CHANGELOG.md` para lo ya hecho.
