"""
Josh AI — Gemini REST client
============================
Talks to Gemini over plain HTTPS with `requests` instead of the
`google-generativeai` SDK. The SDK pulls in grpcio + cryptography, which
try to compile native code on Termux (Android/aarch64) and fail without a
Rust toolchain. This client needs nothing but `requests`.
"""

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT_SECONDS = 30


class GeminiError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")


def generate_content(api_key: str, model: str, prompt: str) -> str:
    """Send a single-turn prompt to Gemini and return the text response."""
    url = f"{API_BASE}/models/{model}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise GeminiError(0, f"Network error reaching Gemini: {exc}")

    if resp.status_code != 200:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except ValueError:
            detail = resp.text
        raise GeminiError(resp.status_code, detail)

    data = resp.json()
    try:
        candidates = data["candidates"]
        parts = candidates[0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError):
        finish_reason = data.get("candidates", [{}])[0].get("finishReason", "unknown")
        raise GeminiError(200, f"No text in response (finishReason: {finish_reason}).")
