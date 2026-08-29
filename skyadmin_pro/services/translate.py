"""Translation via deep-translator (needs internet).

Default workflow: Burmese clients ↔ English. Thai → English is for reading
supplier paperwork; suppliers themselves are contacted in English.
"""

from __future__ import annotations

# (label, source code, target code)
TRANSLATE_DIRECTIONS: tuple[tuple[str, str, str], ...] = (
    ("Burmese → English", "my", "en"),
    ("English → Burmese", "en", "my"),
    ("Thai → English", "th", "en"),
)

DEFAULT_DIRECTION = TRANSLATE_DIRECTIONS[0][0]


def direction_codes(label: str) -> tuple[str, str]:
    for name, source, target in TRANSLATE_DIRECTIONS:
        if name == label:
            return source, target
    return TRANSLATE_DIRECTIONS[0][1], TRANSLATE_DIRECTIONS[0][2]


def translate_text(text: str, source: str, target: str) -> str:
    import socket
    import time

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Paste text to translate.")

    try:
        from deep_translator import GoogleTranslator
    except ImportError as exc:
        raise RuntimeError(
            "deep-translator is not installed. Run: pip install deep-translator"
        ) from exc

    # deep-translator's requests calls have no timeout by default — without
    # this, a half-dead connection hangs the worker thread forever.
    old_timeout = socket.getdefaulttimeout()
    last_exc: Exception | None = None
    try:
        socket.setdefaulttimeout(15)
        for attempt in range(2):
            try:
                result = GoogleTranslator(source=source, target=target).translate(cleaned)
                break
            except Exception as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(1.0)  # brief backoff, then one retry
        else:
            raise RuntimeError(
                "Translation failed. Check the internet connection and try again."
            ) from last_exc
    finally:
        socket.setdefaulttimeout(old_timeout)

    if not result or not str(result).strip():
        raise RuntimeError("No translation returned. Try a shorter passage.")
    return str(result).strip()
