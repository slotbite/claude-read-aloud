#!/usr/bin/env python3
"""Persistent OmniVoice synthesis server (loopback only).

Runs with the python of the OmniVoice venv (torch, omnivoice, soundfile), NOT
with the plugin's stdlib-only interpreter. speak.py starts it on demand and it
shuts itself down after --idle-min minutes without requests, handing the VRAM
back. Loading the model costs ~5 s plus the torch import, which is why it lives
here instead of inside each speak.py (every reply spawns a fresh one).

  GET  /health        {ok, device, loaded, idle_s, voices_cached, pid}
  POST /synth         {text, voice, speed, out, lang}      -> {ok, seconds}
  POST /add-voice     {name, src, text, lang, voices_dir}  -> {ok, text, ...}
  POST /shutdown      stop now

Voices live in <voices-dir>/<name>/{ref.wav,voz.json}. The cloned-voice prompt
(Whisper-free: the transcript is stored) is cached per voice and rebuilt when the
files change.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SR = 24000
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

state = {
    "model": None,
    "device": "?",
    "last": time.time(),
    "busy": 0,
    "prompts": {},  # voice -> (stamp, prompt)
}
gpu_lock = threading.Lock()  # one generation at a time
VOICES_DIR = pathlib.Path(".")


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, file=sys.stderr, flush=True)


def load_model():
    import torch
    from omnivoice import OmniVoice

    if torch.cuda.is_available():
        device, dtype = "cuda:0", torch.float16
    else:
        device, dtype = "cpu", torch.float32
        log("WARNING: no CUDA — running on CPU, this will be slow")
    t0 = time.time()
    state["model"] = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice", device_map=device, dtype=dtype
    )
    state["device"] = device
    log(f"model loaded on {device} in {time.time() - t0:.1f}s")


def read_wav(path):
    import soundfile as sf

    wav, sr = sf.read(str(path), dtype="float32", always_2d=False)
    return wav, sr


def to_mono_24k(wav, sr):
    import numpy as np

    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if sr != SR:
        import torch
        import torchaudio

        wav = (
            torchaudio.functional.resample(torch.from_numpy(wav), sr, SR)
            .numpy()
            .astype(np.float32)
        )
    return wav


def voice_prompt(name: str):
    """Cached clone prompt for a library voice; None means the 'auto' voice."""
    import torch

    if not name or name == "auto":
        return None, None
    if not NAME_RE.match(name):
        raise ValueError(f"bad voice name: {name}")
    d = VOICES_DIR / name
    ref, meta_p = d / "ref.wav", d / "voz.json"
    if not ref.exists():
        raise FileNotFoundError(f"voice '{name}' not in the library")
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
    stamp = (ref.stat().st_mtime_ns, meta_p.stat().st_mtime_ns if meta_p.exists() else 0)
    hit = state["prompts"].get(name)
    if hit and hit[0] == stamp:
        return hit[1], meta.get("idioma")
    wav, sr = read_wav(ref)
    p = state["model"].create_voice_clone_prompt(
        ref_audio=(torch.from_numpy(to_mono_24k(wav, sr)).unsqueeze(0), SR),
        ref_text=meta.get("texto") or None,
    )
    state["prompts"][name] = (stamp, p)
    return p, meta.get("idioma")


def do_synth(q: dict) -> dict:
    import soundfile as sf

    t0 = time.time()
    with gpu_lock:
        prompt, vlang = voice_prompt(q.get("voice") or "")
        speed = float(q.get("speed") or 1.0)
        kw = {"voice_clone_prompt": prompt} if prompt is not None else {}
        audio = state["model"].generate(
            text=q["text"],
            language=q.get("lang") or vlang or None,
            num_step=int(q.get("steps") or 16),
            speed=None if abs(speed - 1.0) < 0.01 else speed,
            **kw,
        )[0]
        if state["device"].startswith("cuda"):
            import torch

            # Hand the generation scratch memory back: the allocator would keep
            # it reserved (several GB) for as long as the server idles.
            torch.cuda.empty_cache()
    out = pathlib.Path(q["out"])
    tmp = out.with_name(out.name + ".part")
    sf.write(str(tmp), audio, SR, format="WAV", subtype="PCM_16")
    os.replace(tmp, out)
    return {"ok": True, "seconds": round(time.time() - t0, 2)}


def do_add_voice(q: dict) -> dict:
    """Store a reference (mono, 24 kHz) and its transcript in the library."""
    import soundfile as sf
    import torch

    name = q["name"]
    if not NAME_RE.match(name):
        raise ValueError("voice names: letters, digits, _ and - (max 64)")
    vdir = pathlib.Path(q.get("voices_dir") or VOICES_DIR) / name
    wav, sr = read_wav(q["src"])
    wav = to_mono_24k(wav, sr)
    dur = len(wav) / SR
    text = (q.get("text") or "").strip()
    transcribed = False
    if not text:
        with gpu_lock:
            m = state["model"]
            m.load_asr_model()
            try:
                text = m.transcribe((wav, SR))
            finally:
                m._asr_pipe = None  # give the ~1.5 GB back
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        transcribed = True
    vdir.mkdir(parents=True, exist_ok=True)
    sf.write(str(vdir / "ref.wav"), wav, SR, format="WAV", subtype="PCM_16")
    meta = {
        "texto": text,
        "idioma": q.get("lang") or "",
        "origen": q.get("origin") or "",
    }
    (vdir / "voz.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    state["prompts"].pop(name, None)
    return {
        "ok": True,
        "text": text,
        "transcribed": transcribed,
        "seconds": round(dur, 1),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a) -> None:  # quiet
        pass

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            vram = 0
            if state["model"] is not None and state["device"].startswith("cuda"):
                import torch

                vram = round(torch.cuda.memory_reserved() / 2**20)
            self._send(
                200,
                {
                    "ok": True,
                    "pid": os.getpid(),
                    "device": state["device"],
                    "loaded": state["model"] is not None,
                    "vram_mb": vram,
                    "idle_s": round(time.time() - state["last"], 1),
                    "voices_cached": sorted(state["prompts"]),
                },
            )
        else:
            self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        state["busy"] += 1
        state["last"] = time.time()
        try:
            n = int(self.headers.get("Content-Length") or 0)
            q = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/synth":
                self._send(200, do_synth(q))
            elif self.path == "/add-voice":
                self._send(200, do_add_voice(q))
            elif self.path == "/shutdown":
                self._send(200, {"ok": True})
                threading.Thread(target=lambda: (time.sleep(0.2), os._exit(0))).start()
            else:
                self._send(404, {"ok": False, "error": "not found"})
        except FileNotFoundError as e:
            self._send(404, {"ok": False, "error": str(e)})
        except Exception as e:  # noqa: BLE001 — report to the client, keep serving
            log(f"error on {self.path}: {e!r}")
            self._send(500, {"ok": False, "error": str(e)[:500]})
        finally:
            state["busy"] -= 1
            state["last"] = time.time()


def watchdog(idle_s: float) -> None:
    while True:
        time.sleep(min(5.0, max(0.5, idle_s / 4)))
        if state["busy"] == 0 and time.time() - state["last"] > idle_s:
            log(f"idle for {idle_s:.0f}s — shutting down to free the GPU")
            os._exit(0)


def main() -> int:
    global VOICES_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7853)
    ap.add_argument("--idle-min", type=float, default=15.0)
    ap.add_argument("--voices-dir", required=True)
    args = ap.parse_args()
    VOICES_DIR = pathlib.Path(args.voices_dir)

    # Bind first: a second server on the same port fails here, fast and cheap.
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    state["last"] = time.time()
    # Serve /health while the model loads; synth requests wait on the load.
    ready = threading.Event()
    real_synth, real_add = do_synth, do_add_voice

    def loader() -> None:
        try:
            load_model()
        except BaseException as e:  # noqa: BLE001 — a dead server beats a hung one
            log(f"model load failed: {e!r}")
            os._exit(1)
        state["last"] = time.time()
        ready.set()

    globals()["do_synth"] = lambda q: (ready.wait(), real_synth(q))[1]
    globals()["do_add_voice"] = lambda q: (ready.wait(), real_add(q))[1]
    threading.Thread(target=loader, daemon=True).start()
    if args.idle_min > 0:
        threading.Thread(target=watchdog, args=(args.idle_min * 60,), daemon=True).start()
    log(f"listening on 127.0.0.1:{args.port} (idle shutdown {args.idle_min} min)")
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
