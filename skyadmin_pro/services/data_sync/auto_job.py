"""Run auto sync work off the UI thread."""

from __future__ import annotations

import logging

from .dirty import clear_dirty
from .refresh import soft_refresh_active_view

logger = logging.getLogger(__name__)


def run_auto_sync_job(scheduler, *, mode: str, reason: str) -> None:
    """Start a background pull/push; ``scheduler`` owns the busy lock."""
    with scheduler._lock:
        if scheduler._busy:
            return
        scheduler._busy = True
    from skyadmin_pro.ui.async_ui import run_background

    def work():
        from .chunk_7 import sync_data

        if mode == "push":
            clear_dirty()
        return sync_data(scheduler.app.db, timeout=25.0, mode=mode)

    def on_success(result) -> None:
        ok, msg = result if isinstance(result, tuple) else (False, str(result))
        if ok and mode == "pull" and "pulled 0" not in str(msg):
            soft_refresh_active_view(scheduler.app)
        if ok:
            try:
                set_status = getattr(scheduler.app, "set_status", None)
                if callable(set_status) and reason != "interval":
                    set_status(str(msg).splitlines()[0][:120])
            except Exception:
                pass
        else:
            logger.info("Auto sync %s failed: %s", reason, msg)

    def done() -> None:
        with scheduler._lock:
            scheduler._busy = False

    run_background(
        scheduler.app,
        work=work,
        on_success=on_success,
        on_error=lambda err: logger.info("Auto sync %s error: %s", reason, err),
        finally_fn=done,
    )
