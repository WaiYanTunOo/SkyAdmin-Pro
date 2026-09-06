"""QThread background-work bridge (Phase 3 shell).

Same callback contract as ``ui.async_ui.run_background`` (work /
on_success / on_error / finally_fn) so view code ports mechanically:
workers run off the GUI thread, results return via queued signals, and
the process-pool offload in ``services.process_jobs`` stays untouched
(binding-agnostic).
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

# Fire-and-forget workers must survive until their thread finishes: the
# returned object is routinely discarded at the call site, and PySide will
# garbage-collect the wrapper mid-flight. The registry holds them; the
# thread-finished handler releases them (deleteLater handles the C++ side).
_LIVE_WORKERS: set = set()


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
