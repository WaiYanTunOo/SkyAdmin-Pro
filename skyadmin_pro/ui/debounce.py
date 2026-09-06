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
            except Exception:  # defensive: Tk teardown/callback
                pass
            after_id[0] = None
        try:
            after_id[0] = widget.after(delay_ms, _run)
        except Exception:
            after_id[0] = None

    def _run() -> None:
        after_id[0] = None
        try:
            if not widget.winfo_exists():
                return
        except Exception:
            return
        callback()

    def cancel() -> None:
        if after_id[0] is not None:
            try:
                widget.after_cancel(after_id[0])
            except Exception:  # defensive: Tk teardown/callback
                pass
            after_id[0] = None

    schedule.cancel = cancel  # type: ignore[attr-defined]
    return schedule
