#!/usr/bin/env python3
"""Save text to temp file for speaking - reads from stdin."""

import sys
import tempfile
import pathlib


def save_text(text):
    """Save text to temp file."""
    temp_file = pathlib.Path(tempfile.gettempdir()) / "opencode-last-reply.txt"
    temp_file.write_text(text, encoding="utf-8")
    print(f"Saved {len(text)} chars")


if __name__ == "__main__":
    # Read from stdin (preserves line breaks)
    text = sys.stdin.read()
    if text.strip():
        save_text(text)
    else:
        # Fallback to command line args
        if len(sys.argv) > 1:
            save_text(" ".join(sys.argv[1:]))
        else:
            print("No text provided")
