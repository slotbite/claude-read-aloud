#!/usr/bin/env python3
"""Get the last assistant message with text from opencode session."""

import json
import subprocess
import tempfile
import pathlib
import sys
import re


def get_session_data():
    """Export current session and parse JSON."""
    # Get session ID
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "opencode session list"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    sessions = re.findall(r"(ses_\w+)", result.stdout)
    if not sessions:
        return None

    session_id = sessions[0]

    # Export to file
    export_file = pathlib.Path(tempfile.gettempdir()) / "opencode-export.json"
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"opencode export {session_id} | Out-File '{export_file}' -Encoding utf8",
        ],
        capture_output=True,
    )

    if not export_file.exists():
        return None

    # Parse JSON
    content = export_file.read_text(encoding="utf-8", errors="replace")
    start = content.find("{")
    end = content.rfind("}") + 1

    if start == -1 or end == 0:
        return None

    try:
        return json.loads(content[start:end])
    except json.JSONDecodeError:
        return None


def get_last_text_message(data):
    """Get the last assistant message with actual text content."""
    if not data:
        return None

    for msg in reversed(data.get("messages", [])):
        if msg.get("info", {}).get("role") != "assistant":
            continue

        parts = msg.get("parts", [])
        # Find text parts that have actual content
        text_parts = [
            p.get("text", "")
            for p in parts
            if p.get("type") == "text" and p.get("text", "").strip()
        ]

        if text_parts:
            return "\n".join(text_parts)

    return None


def main():
    data = get_session_data()
    if not data:
        print("No session data found")
        return 1

    text = get_last_text_message(data)
    if not text:
        print("No assistant text message found")
        return 1

    # Save to temp file
    temp_file = pathlib.Path(tempfile.gettempdir()) / "opencode-last-reply.txt"
    temp_file.write_text(text, encoding="utf-8")
    print(f"Saved {len(text)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
