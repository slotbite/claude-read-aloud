---
description: Pick the reading voice — list, audition, set
argument-hint: [voice id to set directly]
---

If the user supplied an argument, treat it as a voice id: run step 3 with it.

1. List what's available:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --list-voices
```

Show the result as a short readable list (label and id). If it's long, show
the first ~20 and say how many more there are; offer to filter by name.

2. When the user wants to hear one, audition it WITHOUT saving:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --detach --voice VOICE_ID --text "This is how I'd sound reading your replies."
```

Repeat for as many voices as they like.

3. When they choose, save it and confirm in the new voice:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --set-voice VOICE_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --detach --text "Voice saved. This is me from now on."
```

Voices belong to the current provider (see `/read-aloud:speak-status`). To
change provider, edit the config file it names — or `/read-aloud:voice-setup`
installs the free Kokoro voices.

## Cloned voices (provider `omnivoice`)

With provider `omnivoice` the list is `auto` (the model's own voice) plus the
user's library of cloned voices; steps 2 and 3 work unchanged (the first reading
after a while takes ~20 s while the model loads; later ones start in ~1-2 s).
To add a voice from a reference clip (3-15 s of clean speech, any audio file):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/speak.py" --add-voice NAME CLIP.wav --ref-text "what the clip says" --lang es
```

Omit `--ref-text` to have it transcribed (needs a one-time ~1.5GB download) and
show the user the transcript to check. `--remove-voice NAME` deletes one. If the
provider is not `omnivoice` yet: `--set-provider omnivoice` (needs
`speak.py --setup omnivoice` first, NVIDIA GPU recommended). Only clone voices
the user has the right to use.
