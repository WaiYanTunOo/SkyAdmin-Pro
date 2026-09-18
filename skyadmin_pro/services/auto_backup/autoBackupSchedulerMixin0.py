from __future__ import annotations

from datetime import datetime

from skyadmin_pro.db.cipher import DB_ERRORS

from ._const_0 import logger
from ._const_1 import SETTING_AUTO_BACKUP_ENABLED
from ._const_2 import SETTING_AUTO_BACKUP_INTERVAL
from ._const_3 import SETTING_AUTO_BACKUP_LAST_RUN
from .funcs import auto_backups_dir, run_auto_backup, should_run_backup


class AutoBackupSchedulerMixin0:
    """Lightweight scheduler that checks periodically from the main thread."""

    def __init__(self, app) -> None:
        self.app = app
        self._check_interval_ms = 30 * 60 * 1000  # check every 30 minutes
        self._timer_id: str | None = None

    def start(self) -> None:
        """Start periodic backup checks."""
        self._schedule_check()

    def stop(self) -> None:
        """Stop periodic checks."""
        if self._timer_id is not None:
            try:
                self.app.after_cancel(self._timer_id)
            except Exception:  # defensive: after_cancel raises once the timer already fired (Tk)
                pass
            self._timer_id = None

    def nudge(self, *, delay_ms: int = 500) -> None:
        """Re-read settings soon after the user changes toggle/interval in Settings."""
        self.stop()
        try:
            self._timer_id = self.app.after(max(0, int(delay_ms)), self._check)
        except Exception:  # defensive: app.after is unavailable during teardown — fall back to a fresh schedule
            self.start()

    def _schedule_check(self) -> None:
        try:
            self._timer_id = self.app.after(self._check_interval_ms, self._check)
        except Exception:  # defensive: app.after fails during app teardown — nothing to reschedule for
            pass

    def _check(self) -> None:
        try:
            db = self.app.db
            enabled = db.get_setting(SETTING_AUTO_BACKUP_ENABLED)
            if enabled != "1":
                self._schedule_check()
                return
            interval = db.get_setting(SETTING_AUTO_BACKUP_INTERVAL) or "daily"
            last_run = db.get_setting(SETTING_AUTO_BACKUP_LAST_RUN)
            if should_run_backup(db, interval, last_run):
                backup_dir = auto_backups_dir(self.app.paths.root)
                result = run_auto_backup(self.app.paths.root, db.db_file, backup_dir)
                if result:
                    now = datetime.now()
                    db.set_setting(SETTING_AUTO_BACKUP_LAST_RUN, now.isoformat())
                    # Feed the Settings backup banner (same key as manual backups).
                    try:
                        from skyadmin_pro.config.tasks import SETTING_LAST_ENCRYPTED_BACKUP

                        db.set_setting(SETTING_LAST_ENCRYPTED_BACKUP, now.date().isoformat())
                    except DB_ERRORS:
                        logger.warning("Could not update backup banner setting", exc_info=True)
                    # One status-bar toast per run (scheduler ticks on the main thread).
                    try:
                        set_status = getattr(self.app, "set_status", None)
                        if callable(set_status):
                            set_status(f"Auto-backup completed: {result.name}")
                    except Exception:  # defensive: status-bar toast is cosmetic — never fail a completed backup for it
                        logger.debug("Could not show auto-backup toast", exc_info=True)
                    logger.info("Auto-backup completed: %s", result)
        except Exception:  # defensive: scheduler must survive any unexpected failure and keep ticking
            logger.exception("Auto-backup check failed")
        finally:
            self._schedule_check()
