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
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Paste text to translate.")

    try:
        from deep_translator import GoogleTranslator
    except ImportError as exc:
        raise RuntimeError(
            "deep-translator is not installed. Run: pip install deep-translator"
        ) from exc

    try:
        result = GoogleTranslator(source=source, target=target).translate(cleaned)
    except Exception as exc:
        raise RuntimeError(
            "Translation failed. Check the internet connection and try again."
        ) from exc

    if not result or not str(result).strip():
        raise RuntimeError("No translation returned. Try a shorter passage.")
    return str(result).strip()
