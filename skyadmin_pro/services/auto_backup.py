"""Scheduled auto-backup — daily/weekly encrypted backup with notification."""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SETTING_AUTO_BACKUP_ENABLED = "auto_backup_enabled"
SETTING_AUTO_BACKUP_INTERVAL = "auto_backup_interval"  # "daily" | "weekly" | "off"
SETTING_AUTO_BACKUP_LAST_RUN = "auto_backup_last_run"


def should_run_backup(db, interval: str, last_run: str | None) -> bool:
    """Check if a backup should run based on interval and last run timestamp."""
    if interval == "off" or not interval:
        return False
    if not last_run:
        return True
    try:
        last = datetime.fromisoformat(last_run)
    except (ValueError, TypeError):
        return True
    now = datetime.now()
    elapsed = (now - last).total_seconds()
    if interval == "daily":
        return elapsed >= 86400
    if interval == "weekly":
        return elapsed >= 604800
    return False


def run_auto_backup(workspace_root: Path, db_file: Path, backup_dir: Path) -> Path | None:
    """Execute an auto-backup. Returns the backup path on success, None on failure."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    dest = backup_dir / f"SkyAdminPro_AutoBackup_{today}.skybackup"
    # Avoid overwriting same-day backup
    counter = 1
    while dest.exists():
        dest = backup_dir / f"SkyAdminPro_AutoBackup_{today}_{counter}.skybackup"
        counter += 1
    try:
        from skyadmin_pro.services.crypto import create_encrypted_backup
        create_encrypted_backup(workspace_root, db_file, dest)
        logger.info("Auto-backup created: %s", dest)
        return dest
    except Exception:
        logger.exception("Auto-backup failed")
        return None


class AutoBackupScheduler:
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
            except Exception:
                pass
            self._timer_id = None

    def _schedule_check(self) -> None:
        try:
            self._timer_id = self.app.after(self._check_interval_ms, self._check)
        except Exception:
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
                backup_dir = self.app.paths.root / "AutoBackups"
                result = run_auto_backup(self.app.paths.root, db.db_file, backup_dir)
                if result:
                    db.set_setting(SETTING_AUTO_BACKUP_LAST_RUN, datetime.now().isoformat())
                    logger.info("Auto-backup completed: %s", result)
        except Exception:
            logger.exception("Auto-backup check failed")
        finally:
            self._schedule_check()
