"""Tests for the omnivoice provider in scripts/speak.py that need no GPU and no
model: the voice library, voice resolution, server start-up and the provider's
HTTP client, against a fake server standing in for omnivoice_server.py.

Run:  python -m unittest tests.test_omnivoice -v
"""

import contextlib
import io
import json
import pathlib
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import speak  # noqa: E402


class Fake(BaseHTTPRequestHandler):
    calls: list = []

    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, {"ok": True, "device": "cuda:0"})

    def do_POST(self):
        q = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.calls.append((self.path, q))
        if q.get("text") == "boom":
            return self._send(500, {"ok": False, "error": "kaput"})
        if self.path == "/synth":
            pathlib.Path(q["out"]).write_bytes(b"RIFFfake")
        self._send(200, {"ok": True, "text": "dicho", "transcribed": not q.get("text")})


class OmniVoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ra-ov-test-"))
        self._data = speak.data_dir
        speak.data_dir = lambda: self.tmp
        Fake.calls = []
        self.srv = None
        self.addCleanup(setattr, speak, "ov_start_server", speak.ov_start_server)
        self.cfg = dict(speak.DEFAULTS, provider="omnivoice", omnivoice_port=1)

    def tearDown(self):
        speak.data_dir = self._data
        if self.srv:
            self.srv.shutdown()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def serve(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.cfg["omnivoice_port"] = self.srv.server_address[1]

    def lib(self, name, texto="hola", idioma="es"):
        d = self.tmp / "voces" / name
        d.mkdir(parents=True)
        (d / "ref.wav").write_bytes(b"x")
        (d / "voz.json").write_text(
            json.dumps({"texto": texto, "idioma": idioma}), encoding="utf-8"
        )

    # ---- library

    def test_library_lists_only_complete_voices(self):
        self.lib("beta")
        self.lib("alfa", idioma="en")
        (self.tmp / "voces" / "sinref").mkdir()  # no ref.wav: ignored
        (self.tmp / "voces" / "mala voz").mkdir()  # invalid name: ignored
        self.assertEqual([v["id"] for v in speak.library_voices()], ["alfa", "beta"])

    def test_library_empty_when_dir_missing(self):
        self.assertEqual(speak.library_voices(), [])

    def test_check_voice(self):
        self.lib("alfa")
        self.assertEqual(speak.ov_check_voice(""), "auto")
        self.assertEqual(speak.ov_check_voice("auto"), "auto")
        self.assertEqual(speak.ov_check_voice("alfa"), "alfa")
        for bad in ("nope", "../alfa", "a/b"):
            with self.assertRaises(SystemExit):
                speak.ov_check_voice(bad)

    def test_list_voices_has_auto_then_library(self):
        self.lib("alfa", idioma="es")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(speak.list_voices(self.cfg), 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["provider"], "omnivoice")
        self.assertEqual([v["id"] for v in out["voices"]], ["auto", "alfa"])
        self.assertIn("es", out["voices"][1]["label"])

    # ---- config helpers

    def test_python_default_and_override(self):
        self.assertEqual(speak.ov_python(self.cfg).parent.parent.name, "omnivoice-venv")
        self.cfg["omnivoice_python"] = "X:/py.exe"
        self.assertEqual(str(speak.ov_python(self.cfg)).replace("\\", "/"), "X:/py.exe")

    def test_hf_cache_never_touches_hf_home(self):
        self.assertIsNone(speak.ov_hf_cache(self.cfg))
        bench = self.tmp / "bench" / "models" / "hf-omnivoice" / "hub"
        (bench / "models--k2-fsa--OmniVoice").mkdir(parents=True)
        self.assertEqual(speak.ov_hf_cache(self.cfg), str(bench))
        self.cfg["omnivoice_hf_cache"] = "D:/hub"
        self.assertEqual(speak.ov_hf_cache(self.cfg), "D:/hub")

    # ---- server lifecycle and client

    def test_ensure_does_not_start_a_running_server(self):
        self.serve()
        speak.ov_start_server = lambda cfg: self.fail("must not start")
        self.assertTrue(speak.ov_ensure(self.cfg)["ok"])

    def test_ensure_starts_server_and_waits(self):
        started = []
        orig = speak.ov_start_server
        self.addCleanup(setattr, speak, "ov_start_server", orig)
        speak.ov_start_server = lambda cfg: (started.append(1), self.serve())
        self.assertEqual(speak.ov_health(dict(self.cfg, omnivoice_port=1)), None)
        self.assertTrue(speak.ov_ensure(self.cfg)["ok"])
        self.assertEqual(started, [1])

    def test_start_without_venv_explains(self):
        with self.assertRaises(SystemExit) as e:
            speak.ov_start_server(self.cfg)
        self.assertIn("--setup omnivoice", str(e.exception))

    def test_synth_posts_voice_speed_and_out(self):
        self.serve()
        self.lib("alfa")
        self.cfg.update(voice="alfa", speed=1.25, omnivoice_lang="es")
        synth = speak.make_synth(self.cfg)
        out = self.tmp / "o.wav"
        synth("hola mundo", out)
        path, q = Fake.calls[-1]
        self.assertEqual(path, "/synth")
        self.assertEqual(
            (q["text"], q["voice"], q["speed"], q["lang"], q["out"]),
            ("hola mundo", "alfa", 1.25, "es", str(out)),
        )
        self.assertTrue(out.exists())

    def test_default_voice_is_auto(self):
        self.serve()
        self.cfg["voice"] = ""
        speak.make_synth(self.cfg)("x", self.tmp / "o.wav")
        self.assertEqual(Fake.calls[-1][1]["voice"], "auto")

    def test_server_error_surfaces(self):
        self.serve()
        synth = speak.make_synth(self.cfg)
        with self.assertRaises(RuntimeError) as e:
            synth("boom", self.tmp / "o.wav")
        self.assertIn("kaput", str(e.exception))

    def test_add_voice_validates_then_posts(self):
        self.serve()
        src = self.tmp / "clip.wav"
        src.write_bytes(b"x")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(speak.add_voice(self.cfg, "bad name", str(src), "", ""), 2)
            self.assertEqual(speak.add_voice(self.cfg, "ok", str(self.tmp / "no"), "", ""), 2)
        self.assertEqual(Fake.calls, [])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(speak.add_voice(self.cfg, "ok", str(src), "", "es"), 0)
        path, q = Fake.calls[-1]
        self.assertEqual(path, "/add-voice")
        self.assertEqual((q["name"], q["lang"], q["text"]), ("ok", "es", ""))
        self.assertEqual(q["voices_dir"], str(self.tmp / "voces"))

    def test_remove_voice(self):
        self.lib("alfa")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(speak.remove_voice("alfa"), 0)
        self.assertEqual(speak.library_voices(), [])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(speak.remove_voice("alfa"), 1)


if __name__ == "__main__":
    unittest.main()
