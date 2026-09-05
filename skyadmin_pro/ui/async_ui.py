"""Marshal background work back to the Tk main thread with safe error surfacing."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

_log = logging.getLogger(__name__)


def _feedback_for(widget) -> Any | None:
    feedback = getattr(widget, "feedback", None)
    if feedback is not None:
        return feedback
    for name in ("translator_feedback", "hub_feedback"):
        candidate = getattr(widget, name, None)
        if candidate is not None:
            return candidate
    return None


def run_on_main(widget, fn: Callable[[], None], *, feedback=None) -> None:
    """Schedule ``fn`` on the Tk main loop; catch UI exceptions."""

    def wrapped() -> None:
        try:
            if not widget.winfo_exists():
                return
            fn()
        except Exception as exc:
            _log.exception("UI callback failed")
            target = feedback if feedback is not None else _feedback_for(widget)
            if target is not None and hasattr(target, "error"):
                target.error(str(exc))

    try:
        widget.after(0, wrapped)
    except Exception:
        _log.exception("Failed to schedule UI callback")


def run_background(
    widget,
    *,
    work: Callable[[], Any],
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    finally_fn: Callable[[], None] | None = None,
    feedback=None,
) -> None:
    """Run ``work`` in a daemon thread; invoke callbacks on the main thread."""

    def worker() -> None:
        result: Any = None
        err: str | None = None
        try:
            result = work()
        except Exception as exc:
            _log.exception("Background work failed")
            err = str(exc)

        def done() -> None:
            try:
                if not widget.winfo_exists():
                    return
                if err:
                    if on_error:
                        on_error(err)
                    else:
                        target = feedback if feedback is not None else _feedback_for(widget)
                        if target is not None and hasattr(target, "error"):
                            target.error(err)
                elif on_success is not None:
                    on_success(result)
            except Exception as exc:
                _log.exception("Background UI callback failed")
                if on_error:
                    on_error(str(exc))
                else:
                    target = feedback if feedback is not None else _feedback_for(widget)
                    if target is not None and hasattr(target, "error"):
                        target.error(str(exc))
            finally:
                if finally_fn:
                    try:
                        finally_fn()
                    except Exception:
                        _log.exception("Background finally_fn failed")

        run_on_main(widget, done, feedback=feedback)

    threading.Thread(target=worker, daemon=True).start()
