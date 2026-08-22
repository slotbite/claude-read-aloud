#!/usr/bin/env python3
"""Wrapper for /speak command in opencode - reads from temp file."""

import sys
import pathlib
import tempfile
import subprocess

LAST_REPLY_FILE = pathlib.Path(tempfile.gettempdir()) / "opencode-last-reply.txt"
SCRIPT = pathlib.Path("C:/GIT/claude-read-aloud/scripts/speak.py")


def main():
    if not LAST_REPLY_FILE.exists():
        print("No hay respuesta para leer. Espera a que termine una respuesta.")
        return 1

    text = LAST_REPLY_FILE.read_text(encoding="utf-8").strip()
    if not text:
        print("Archivo de respuesta vacío.")
        return 1

    # Truncate if too long
    if len(text) > 5000:
        text = text[:5000] + "..."

    # Escape for shell
    escaped = text.replace('"', '\\"').replace("\n", " ")

    cmd = f'python "{SCRIPT}" --detach --text "{escaped}"'
    subprocess.run(cmd, shell=True)
    print("reading aloud")
    return 0


if __name__ == "__main__":
    sys.exit(main())
