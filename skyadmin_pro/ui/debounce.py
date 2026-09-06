"""Shared UI debounce helper for search fields."""

from __future__ import annotations

from collections.abc import Callable


def debounced_after(widget, callback: Callable[[], None], delay_ms: int = 300) -> Callable[[], None]:
    """Return a callable suitable for ``trace_add('write', ...)`` that debounces *callback*."""
    after_id: list[str | None] = [None]

    def schedule(*_args) -> None:
        if after_id[0] is not None:
            try:
                widget.after_cancel(after_id[0])
            except Exception:
                pass
        after_id[0] = widget.after(delay_ms, _run)

    def _run() -> None:
        after_id[0] = None
        if widget.winfo_exists():
            callback()

    def cancel() -> None:
        if after_id[0] is not None:
            try:
                widget.after_cancel(after_id[0])
            except Exception:
                pass
            after_id[0] = None

    schedule.cancel = cancel  # type: ignore[attr-defined]
    return schedule
