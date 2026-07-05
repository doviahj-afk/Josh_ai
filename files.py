"""File tools — all operations are confined to SANDBOX_DIR to prevent the
agent from reading or overwriting files elsewhere on the device."""

import os

from config import SANDBOX_DIR


def _safe_path(filename: str) -> str:
    filename = filename.strip().lstrip("/")
    full = os.path.normpath(os.path.join(SANDBOX_DIR, filename))
    if not full.startswith(os.path.normpath(SANDBOX_DIR)):
        raise ValueError("Path escapes the sandbox directory.")
    return full


def read_file(filename: str) -> str:
    try:
        path = _safe_path(filename)
        if not os.path.exists(path):
            return f"File not found: {filename}"
        with open(path, "r", errors="replace") as f:
            content = f.read()
        return content[:4000]
    except Exception as exc:
        return f"Error reading file: {exc}"


def write_file(payload: str) -> str:
    try:
        if "|||" not in payload:
            return "Error: expected input format 'filename|||content'."
        filename, content = payload.split("|||", 1)
        path = _safe_path(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Wrote {len(content)} characters to {filename.strip()}"
    except Exception as exc:
        return f"Error writing file: {exc}"


def list_files(_: str = "") -> str:
    try:
        entries = []
        for root, _dirs, files in os.walk(SANDBOX_DIR):
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), SANDBOX_DIR)
                entries.append(rel)
        return "\n".join(entries) if entries else "(sandbox is empty)"
    except Exception as exc:
        return f"Error listing files: {exc}"
