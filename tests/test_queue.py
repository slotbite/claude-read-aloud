"""Tests for the global reading queue in scripts/speak.py. No audio is played:
each "reading" is a fake that appends start/end lines to a log file.

Run:  python -m unittest tests.test_queue -v
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import speak  # noqa: E402

# A child process that takes a turn for SESSION and "plays" for DUR seconds.
DRIVER = """
import os, pathlib, sys, time
sys.path.insert(0, {scripts!r})
import speak
speak.QUEUE_ROOT = pathlib.Path(os.environ["Q"])
log = pathlib.Path(os.environ["LOG"])
sess, dur = sys.argv[1], float(sys.argv[2])
tag = sys.argv[3]
def play(prev):
    with open(log, "a") as f: f.write("start " + tag + " prev=" + prev + "\\n")
    time.sleep(dur)
    with open(log, "a") as f: f.write("end " + tag + "\\n")
ok = speak.run_turn(sess, play, max_wait=30)
"""


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ra-queue-test-"))
        self.q = self.tmp / "q"
        self.log = self.tmp / "log.txt"
        self.log.write_text("")
        self.procs = []
        speak.QUEUE_ROOT = self.q

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                speak.kill_tree(p.pid)
            p.wait()
        speak.QUEUE_ROOT = None
        shutil.rmtree(self.tmp, ignore_errors=True)

    def start(self, session, dur, tag):
        env = dict(os.environ, Q=str(self.q), LOG=str(self.log))
        p = subprocess.Popen(
            [sys.executable, "-c", DRIVER.format(scripts=str(SCRIPTS)), session, str(dur), tag],
            env=env,
        )
        self.procs.append(p)
        return p

    def events(self):
        return [l.split(" prev=")[0] for l in self.log.read_text().splitlines() if l]

    def wait_for(self, line, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            if any(e == line for e in self.events()):
                return
            time.sleep(0.05)
        self.fail(f"timed out waiting for {line!r}; log={self.events()}")

    def test_fifo_between_sessions_never_overlaps(self):
        self.start("A", 1.0, "a")
        self.wait_for("start a")
        self.start("B", 0.3, "b")
        time.sleep(0.3)
        self.start("C", 0.3, "c")
        for p in self.procs:
            p.wait(timeout=30)
        self.assertEqual(
            self.events(),
            ["start a", "end a", "start b", "end b", "start c", "end c"],
        )

    def test_same_session_replaces_playing_reading(self):
        a1 = self.start("A", 30, "a1")
        self.wait_for("start a1")
        a2 = self.start("A", 0.2, "a2")
        a2.wait(timeout=30)
        a1.wait(timeout=10)
        self.assertEqual(self.events(), ["start a1", "start a2", "end a2"])

    def test_same_session_replaces_waiting_reading(self):
        self.start("A", 2.5, "a")
        self.wait_for("start a")
        b1 = self.start("B", 0.2, "b1")
        time.sleep(0.8)  # b1 is now waiting in the queue
        b2 = self.start("B", 0.2, "b2")
        for p in self.procs:
            p.wait(timeout=30)
        self.assertEqual(
            self.events(), ["start a", "end a", "start b2", "end b2"]
        )
        self.assertNotEqual(b1.returncode, None)

    def test_stop_without_session_stops_all_and_clears_queue(self):
        a = self.start("A", 30, "a")
        self.wait_for("start a")
        b = self.start("B", 0.2, "b")
        time.sleep(0.8)
        speak.stop(None)
        a.wait(timeout=10)
        b.wait(timeout=10)
        self.assertEqual(self.events(), ["start a"])
        self.assertEqual(list(self.q.glob("*.req")), [])
        self.assertFalse((self.q / "playing.lock").exists())

    def test_stop_with_session_only_touches_that_session(self):
        a = self.start("A", 30, "a")
        self.wait_for("start a")
        b = self.start("B", 0.2, "b")
        time.sleep(0.8)
        speak.stop("B")  # B is queued: removed; A keeps playing
        b.wait(timeout=10)
        self.assertIsNone(a.poll())
        self.assertTrue((self.q / "playing.lock").exists())
        speak.stop("A")
        a.wait(timeout=10)
        self.assertEqual(self.events(), ["start a"])

    def test_orphan_lock_is_recovered(self):
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        self.q.mkdir(parents=True, exist_ok=True)
        (self.q / "playing.lock").write_text(f"{dead.pid}\nGHOST")
        (self.q / f"{time.time_ns() - 10**9:020d}_{dead.pid}_GHOST.req").write_text("")
        p = self.start("A", 0.1, "a")
        p.wait(timeout=30)
        self.assertEqual(self.events(), ["start a", "end a"])
        self.assertEqual(list(self.q.glob("*.req")), [])

    def test_pid_alive(self):
        self.assertTrue(speak.pid_alive(os.getpid()))
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        self.assertFalse(speak.pid_alive(dead.pid))

    def test_sanitize_session(self):
        self.assertEqual(speak.sanitize_session("a/b\\c:d_e"), "a-b-c-d-e")
        self.assertEqual(speak.sanitize_session(""), "")
        self.assertEqual(speak.sanitize_session("../.."), "")


if __name__ == "__main__":
    unittest.main()
