"""Marshal background work back to the Tk main thread with safe error surfacing."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from typing import Any

_log = logging.getLogger(__name__)

# Thread-safe handoff: workers NEVER call widget.after() (raises
# "main thread is not in main loop" off mainloop). They enqueue; a pump
# scheduled on the main thread drains the queue via after().
_QUEUE: queue.Queue = queue.Queue()
_ACTIVE = 0
_ACTIVE_LOCK = threading.RLock()


def _feedback_for(widget) -> Any | None:
    feedback = getattr(widget, "feedback", None)
    if feedback is not None:
        return feedback
    for name in ("translator_feedback", "hub_feedback"):
        candidate = getattr(widget, name, None)
        if candidate is not None:
            return candidate
    return None


def _drain_queue() -> None:
    """Run all queued main-thread callbacks (main thread only)."""
    while True:
        try:
            target, fn = _QUEUE.get_nowait()
        except queue.Empty:
            return
        try:
            try:
                exists = target.winfo_exists()
            except Exception:
                continue
            if not exists:
                continue
            fn()
        except Exception:
            _log.exception("Queued UI callback failed")


def _pump(widget) -> None:
    """Main-thread pump: drain queue, reschedule while workers remain."""
    widget._async_pump_after = None
    try:
        _drain_queue()
    except Exception:
        _log.exception("UI queue drain failed")
    with _ACTIVE_LOCK:
        active = _ACTIVE
    try:
        pending = not _QUEUE.empty()
    except Exception:
        pending = False
    if active or pending:
        try:
            exists = widget.winfo_exists()
        except Exception:
            return
        if not exists:
            return
        try:
            widget._async_pump_after = widget.after(50, lambda: _pump(widget))
        except Exception:
            widget._async_pump_after = None


def cancel_pump(widget) -> None:
    """Cancel a pending pump scheduled by :func:`run_background`."""
    after_id = getattr(widget, "_async_pump_after", None)
    if after_id is None:
        return
    try:
        widget._async_pump_after = None
    except Exception:
        pass
    try:
        widget.after_cancel(after_id)
    except Exception:
        pass


def run_on_main(widget, fn: Callable[[], None], *, feedback=None) -> None:
    """Schedule ``fn`` on the Tk main loop; catch UI exceptions.

    Must be called on the main thread. Background threads must go
    through :func:`run_background` (queue handoff) instead of calling
    ``widget.after()`` directly.
    """

    def wrapped() -> None:
        try:
            try:
                exists = widget.winfo_exists()
            except Exception:
                return
            if not exists:
                return
            fn()
        except Exception as exc:
            _log.exception("UI callback failed")
            target = feedback if feedback is not None else _feedback_for(widget)
            if target is not None and hasattr(target, "error"):
                try:
                    target.error(str(exc))
                except Exception:
                    pass

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
    """Run ``work`` in a daemon thread; invoke callbacks on the main thread.

    Thread-safe: the worker enqueues ``done`` instead of calling
    ``widget.after()`` itself (which raises off ``mainloop``). A pump
    scheduled here on the calling (main) thread drains the queue.
    """

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
                try:
                    exists = widget.winfo_exists()
                except Exception:
                    return
                if not exists:
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
                    try:
                        on_error(str(exc))
                    except Exception:
                        pass
                else:
                    target = feedback if feedback is not None else _feedback_for(widget)
                    if target is not None and hasattr(target, "error"):
                        try:
                            target.error(str(exc))
                        except Exception:
                            pass
            finally:
                if finally_fn:
                    try:
                        finally_fn()
                    except Exception:
                        _log.exception("Background finally_fn failed")

        _QUEUE.put((widget, done))
        with _ACTIVE_LOCK:
            global _ACTIVE
            _ACTIVE -= 1

    with _ACTIVE_LOCK:
        global _ACTIVE
        _ACTIVE += 1
    # Scheduled on the calling (main) thread — safe even under app.update().
    # Reuse an already-pending pump instead of stacking one per call.
    try:
        if getattr(widget, "_async_pump_after", None) is None:
            widget._async_pump_after = widget.after(0, lambda: _pump(widget))
    except Exception:
        _log.exception("Failed to schedule UI pump")
        try:
            widget._async_pump_after = None
        except Exception:
            pass
        with _ACTIVE_LOCK:
            _ACTIVE -= 1
        return
    threading.Thread(target=worker, daemon=True).start()
