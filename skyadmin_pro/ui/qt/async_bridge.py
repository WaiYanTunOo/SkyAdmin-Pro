"""QThread background-work bridge (Phase 3 shell).

Same callback contract as ``ui.async_ui.run_background`` (work /
on_success / on_error / finally_fn) so view code ports mechanically:
workers run off the GUI thread, results return via queued signals, and
the process-pool offload in ``services.process_jobs`` stays untouched
(binding-agnostic).
"""

from __future__ import annotations

import atexit
import logging
import traceback
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

# Fire-and-forget workers must survive until their thread finishes: the
# returned object is routinely discarded at the call site, and PySide will
# garbage-collect the wrapper mid-flight. The registry holds them; the
# finished handler releases them (deleteLater handles the C++ side).
_LIVE_WORKERS: set = set()


def _is_valid(obj: object) -> bool:
    """Shiboken validity probe — never raises, even on dead wrappers."""
    try:
        import shiboken6

        return bool(shiboken6.isValid(obj))
    except Exception:
        return False


def _shutdown_workers(timeout_ms: int = 5000) -> None:
    """Join outstanding workers at app/pytest teardown.

    Call while Qt is still alive (QApplication.aboutToQuit, or test
    teardown). Late interpreter-exit calls are best-effort only: wrappers
    whose C++ side is already gone are discarded untouched — probing them
    would segfault (no Python exception to catch).
    """
    for worker in list(_LIVE_WORKERS):
        _LIVE_WORKERS.discard(worker)
        try:
            thread = getattr(worker, "_thread", None)
            if thread is None or not _is_valid(thread):
                continue
            try:
                if thread.isRunning():
                    thread.quit()
            except Exception:
                pass
            try:
                thread.wait(timeout_ms)
            except Exception:
                pass
        except Exception:
            pass


def drain_workers(timeout_s: float = 15.0) -> bool:
    """Pump the GUI event loop until live workers finish. Returns True if empty.

    Test teardown (and orderly app shutdown) should drain rather than
    abandon workers: callbacks land on live widgets instead of racing
    window destruction. Stragglers are quit + joined by _shutdown_workers.
    """
    import time

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return not _LIVE_WORKERS
    deadline = time.time() + max(0.0, float(timeout_s))
    app = QApplication.instance()
    while _LIVE_WORKERS and time.time() < deadline:
        try:
            if app is not None:
                app.processEvents()
        except Exception:
            pass
        time.sleep(0.02)
    try:
        if app is not None:
            app.processEvents()
    except Exception:
        pass
    if _LIVE_WORKERS:
        _shutdown_workers()
    return not _LIVE_WORKERS


atexit.register(_shutdown_workers)


def run_background_q(
    parent,
    *,
    work: Callable[[], Any],
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    finally_fn: Callable[[], None] | None = None,
) -> Any:
    """Run *work* in a QThread; deliver callbacks on the GUI thread.

    Returns the worker object (already started). Callbacks are connected
    with queued delivery, so they always run on the receiver's thread.
    """
    from PySide6.QtCore import QObject, QThread, Signal

    class _Worker(QObject):
        finished = Signal(object, object)  # (result, error_text or None)

        def __init__(self) -> None:
            super().__init__()
            self._thread = QThread(parent)
            self.moveToThread(self._thread)
            self._thread.started.connect(self._run)
            self.finished.connect(self._thread.quit)

        def _run(self) -> None:
            result: Any = None
            error: str | None = None
            try:
                result = work()
            except Exception as exc:
                log.exception("Qt background work failed")
                error = str(exc) or traceback.format_exc(limit=3)
            self.finished.emit(result, error)

        def start(self) -> _Worker:
            self._thread.start()
            return self

    worker = _Worker()

    class _Sink(QObject):
        """Lives on the GUI thread; re-emits worker results there."""

        relay = Signal(object, object)

    # The worker object moves to its thread, so slots connected directly to
    # worker.finished would run IN that thread. The sink stays parented to
    # the GUI thread, making relay delivery queued (GUI thread) always.
    sink = _Sink(parent)

    def _deliver(result: Any, error: str | None) -> None:
        try:
            if error:
                if on_error is not None:
                    on_error(error)
            elif on_success is not None:
                on_success(result)
        except Exception:
            log.exception("Qt background callback failed")
        finally:
            if finally_fn is not None:
                try:
                    finally_fn()
                except Exception:
                    log.exception("Qt background finally_fn failed")

    sink.relay.connect(_deliver)
    worker.finished.connect(sink.relay.emit)
    worker.finished.connect(worker.deleteLater)
    worker._thread.finished.connect(worker._thread.deleteLater)
    worker._thread.finished.connect(sink.deleteLater)
    _LIVE_WORKERS.add(worker)
    # Release when the work finishes (worker thread, direct call — set ops
    # are GIL-atomic), not on thread exit: deleteLater ordering otherwise
    # strands wrappers when the event loop is busy.
    worker.finished.connect(lambda _r=None, _e=None: _LIVE_WORKERS.discard(worker))
    return worker.start()
