"""Background auto sync: interval pull + debounced dirty push."""

from __future__ import annotations

import logging
import threading

from .auto_job import run_auto_sync_job
from .chunk_4 import is_data_sync_enabled
from .dirty import is_dirty, set_dirty_handler
from .interval import parse_sync_auto_interval_seconds

logger = logging.getLogger(__name__)

_PUSH_DEBOUNCE_MS = 1500


class AutoSyncScheduler:
    """Main-thread timers for pull interval and debounced push after writes."""

    def __init__(self, app, *, debounce_ms: int = _PUSH_DEBOUNCE_MS) -> None:
        self.app = app
        self.debounce_ms = max(500, int(debounce_ms))
        self._pull_timer: str | None = None
        self._push_timer: str | None = None
        self._busy = False
        self._lock = threading.Lock()

    def start(self) -> None:
        set_dirty_handler(self._on_dirty)
        self._schedule_pull()

    def stop(self) -> None:
        set_dirty_handler(None)
        self._cancel(self._pull_timer)
        self._cancel(self._push_timer)
        self._pull_timer = self._push_timer = None

    def nudge(self) -> None:
        """Re-read interval after Settings changes."""
        self._cancel(self._pull_timer)
        self._pull_timer = None
        self._schedule_pull()

    def on_window_focus(self) -> None:
        if self._auto_pull_seconds() is None:
            return
        run_auto_sync_job(self, mode="pull", reason="focus")

    def _on_dirty(self) -> None:
        if not self._sync_on():
            return
        self._cancel(self._push_timer)
        try:
            self._push_timer = self.app.after(self.debounce_ms, self._debounced_push)
        except Exception:
            self._push_timer = None

    def _debounced_push(self) -> None:
        self._push_timer = None
        if not self._sync_on() or not is_dirty():
            return
        run_auto_sync_job(self, mode="push", reason="dirty")

    def _schedule_pull(self) -> None:
        seconds = self._auto_pull_seconds()
        if seconds is None:
            return
        try:
            self._pull_timer = self.app.after(seconds * 1000, self._interval_pull)
        except Exception:
            self._pull_timer = None

    def _interval_pull(self) -> None:
        self._pull_timer = None
        try:
            if self._auto_pull_seconds() is not None:
                run_auto_sync_job(self, mode="pull", reason="interval")
        finally:
            self._schedule_pull()

    def _sync_on(self) -> bool:
        try:
            return is_data_sync_enabled(self.app.db)
        except Exception:
            return False

    def _auto_pull_seconds(self) -> int | None:
        if not self._sync_on():
            return None
        from skyadmin_pro.config import SETTING_SYNC_AUTO_INTERVAL

        try:
            raw = self.app.db.get_setting(SETTING_SYNC_AUTO_INTERVAL)
        except Exception:
            raw = None
        return parse_sync_auto_interval_seconds(raw)

    def _cancel(self, timer_id: str | None) -> None:
        if timer_id is None:
            return
        try:
            self.app.after_cancel(timer_id)
        except Exception:
            pass
