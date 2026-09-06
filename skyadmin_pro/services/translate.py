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

#: Per-attempt network timeout. deep-translator 1.x exposes no timeout knob,
#: so the call runs on a daemon thread and we join with this budget instead.
TRANSLATE_TIMEOUT_S = 15.0


def direction_codes(label: str) -> tuple[str, str]:
    for name, source, target in TRANSLATE_DIRECTIONS:
        if name == label:
            return source, target
    return TRANSLATE_DIRECTIONS[0][1], TRANSLATE_DIRECTIONS[0][2]


def _translate_once(translator, text: str) -> str:
    """Run one blocking translate call with a timeout (daemon thread + join).

    The worker is daemonic so a timed-out call never outlives the process;
    callers must already be off the UI thread (utilities view uses
    ``run_background``) since join + the single retry sleep block.
    """
    import threading

    box: dict[str, object] = {}

    def _work() -> None:
        try:
            box["result"] = translator.translate(text)
        except Exception as exc:  # noqa: BLE001 — captured and re-raised below
            box["error"] = exc

    worker = threading.Thread(target=_work, daemon=True)
    worker.start()
    worker.join(TRANSLATE_TIMEOUT_S)
    if worker.is_alive():
        raise TimeoutError(f"Translation timed out after {int(TRANSLATE_TIMEOUT_S)}s.")
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box.get("result", "")  # type: ignore[return-value]


def translate_text(text: str, source: str, target: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Paste text to translate.")

    try:
        from deep_translator import GoogleTranslator
    except ImportError as exc:
        raise RuntimeError("deep-translator is not installed. Run: pip install deep-translator") from exc

    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            result = _translate_once(GoogleTranslator(source=source, target=target), cleaned)
            break
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                import time

                time.sleep(1.0)
    else:
        raise RuntimeError("Translation failed. Check the internet connection and try again.") from last_exc

    if not result or not str(result).strip():
        raise RuntimeError("No translation returned. Try a shorter passage.")
    return str(result).strip()
