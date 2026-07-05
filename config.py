"""
Josh AI — Configuration & API key validation
=============================================
Handles loading the Gemini API key and running a cheap live check against
the API so key problems are caught immediately with a clear message,
instead of failing deep inside a chat loop.
"""

import os
import sys

DEFAULT_MODEL = os.environ.get("JOSH_MODEL", "gemini-2.5-flash")
MEMORY_DIR = os.path.join(os.path.expanduser("~"), ".josh_ai")
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")
SANDBOX_DIR = os.path.join(MEMORY_DIR, "sandbox")


def _load_dotenv_if_present():
    """Lightweight .env loader so users don't need python-dotenv installed."""
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_api_key():
    _load_dotenv_if_present()
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key


def validate_api_key(key: str):
    """
    Does a minimal live call to Gemini to confirm the key actually works.
    Returns (ok: bool, message: str).
    """
    if not key:
        return False, (
            "No GEMINI_API_KEY found.\n"
            "Set it with:\n"
            "  export GEMINI_API_KEY=\"your_key_here\"\n"
            "Get a free key at https://aistudio.google.com/apikey"
        )

    if not (key.startswith("AQ.") or key.startswith("AIza")):
        return False, (
            "That doesn't look like a Gemini API key. Valid formats are the newer "
            "'AQ.' auth keys or the older 'AIza' standard keys.\n"
            "Get one at https://aistudio.google.com/apikey"
        )

    from gemini_client import generate_content, GeminiError

    try:
        text = generate_content(key, DEFAULT_MODEL, "Reply with exactly: OK")
        if not text:
            return False, "Key accepted but the model returned an empty response — try again."
        return True, f"API key valid. Model '{DEFAULT_MODEL}' responded: {text!r}"
    except GeminiError as exc:
        msg = exc.message
        if exc.status_code == 400:
            return False, (
                "Gemini rejected the key as invalid.\n"
                "Common causes:\n"
                "  - Key was copied with a trailing space or missing characters\n"
                "  - Key was revoked or belongs to a deleted project\n"
                "  - A standard (AIza) key that's now unrestricted-blocked — "
                "either restrict it to the Gemini API in AI Studio, or switch to "
                "a newer 'AQ.' auth key\n"
                "Generate a fresh one at https://aistudio.google.com/apikey"
            )
        if exc.status_code == 403:
            return False, (
                "Permission denied. The Generative Language API may not be enabled "
                "for this key's project, or the key has restrictions attached in "
                "Google Cloud Console (API restrictions / referrer restrictions)."
            )
        if exc.status_code == 429:
            deprecated_hint = ""
            if DEFAULT_MODEL in ("gemini-2.0-flash", "gemini-2.0-flash-lite"):
                deprecated_hint = (
                    f"\nLikely cause: '{DEFAULT_MODEL}' was deprecated and fully "
                    "retired on June 1, 2026 — it no longer has any free-tier quota "
                    "(that's why the limit shows as 0), regardless of your account. "
                    "Set JOSH_MODEL=gemini-2.5-flash (or gemini-3.1-flash-lite) instead.\n"
                )
            return False, (
                f"Rate limit / quota exceeded. Google's message: {msg!r}\n"
                f"{deprecated_hint}"
                "Other things to check if you're already on a current model:\n"
                "  - Exact quota at https://aistudio.google.com/apikey\n"
                "  - Requests-per-minute limits (free tier is a handful of RPM on most models)\n"
                "  - Whether billing is linked, which can affect tier assignment"
            )
        if exc.status_code == 404:
            return False, f"Model '{DEFAULT_MODEL}' not found for this API version. Try setting JOSH_MODEL=gemini-2.5-flash."
        if exc.status_code == 0:
            return False, f"Network error: {msg}. Check your internet connection."
        return False, f"Unexpected error validating key ({exc.status_code}): {msg}"


def ensure_dirs():
    os.makedirs(MEMORY_DIR, exist_ok=True)
    os.makedirs(SANDBOX_DIR, exist_ok=True)


def bootstrap_or_exit():
    """Call at startup: validates the key and exits with a clear message if broken."""
    ensure_dirs()
    key = get_api_key()
    ok, message = validate_api_key(key)
    print(("[josh-ai] " + message))
    if not ok:
        sys.exit(1)
    return key
