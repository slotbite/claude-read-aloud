---
description: Install the free Kokoro neural voice (one-time ~340MB download; big upgrade on Linux)
---

Run this bash command with a **10-minute timeout** and relay its progress
lines to the user as they appear (it creates a private virtualenv, installs
kokoro-onnx, and downloads the voice model — a few minutes on first run):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --setup kokoro
```

When it finishes successfully, demo the new voice:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --detach --text "Kokoro is installed. This is your new reading voice."
```

Then tell the user setup is done and that `voice` in the config file the
output named can be any of the 54 Kokoro voices (am_michael, af_heart,
bf_emma, …). If either step fails, show the error and do not guess at fixes.

## Voice cloning (OmniVoice) — only if the user asks for it

For cloned voices on a machine with an NVIDIA GPU, run instead (same 10-minute
timeout; it installs torch, omnivoice and fetches a ~3.3GB model):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --setup omnivoice
```

It does not change the provider. Afterwards guide the user: add a voice with
`--add-voice` (see `/read-aloud:voice`), then `--set-provider omnivoice` and
`--set-voice NAME`. `speak.py --status` shows whether the venv and the server
are up. Without a CUDA GPU it runs on CPU, which is slow — say so.
