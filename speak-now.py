#!/usr/bin/env python3
"""Speak the last message - reads from temp file."""

import subprocess
import sys
import tempfile
import pathlib


def speak_from_file():
    """Read and speak from the temp file."""
    temp_file = pathlib.Path(tempfile.gettempdir()) / "opencode-last-reply.txt"

    if not temp_file.exists():
        print("No message file found. Run get-last-message.py first.")
        return

    text = temp_file.read_text(encoding="utf-8").strip()
    if not text:
        print("Message file is empty.")
        return

    # Truncate if too long
    if len(text) > 5000:
        text = text[:5000] + "..."

    # Escape for shell
    escaped = text.replace('"', '\\"').replace("\n", " ")

    subprocess.run(
        f'python "C:\\GIT\\claude-read-aloud\\scripts\\speak.py" --detach --text "{escaped}"',
        shell=True,
    )


if __name__ == "__main__":
    speak_from_file()
