"""Scheduled auto-backup — daily/weekly encrypted backup with notification."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path

from skyadmin_pro.db.cipher import DB_ERRORS

logger = logging.getLogger(__name__)

SETTING_AUTO_BACKUP_ENABLED = "auto_backup_enabled"
SETTING_AUTO_BACKUP_INTERVAL = "auto_backup_interval"  # "daily" | "weekly" | "off"
SETTING_AUTO_BACKUP_LAST_RUN = "auto_backup_last_run"

#: Encrypted auto-backups retained in AutoBackups/ (matches db auto_backup keep).
AUTO_BACKUP_KEEP = 7


def retention_help_text(keep: int = AUTO_BACKUP_KEEP) -> str:
    """User-facing Settings copy for how many AutoBackups files are kept."""
    return (
        f"Keeps the newest {keep} encrypted backups in the AutoBackups folder. "
        "Older files are deleted automatically after each successful run."
    )


def auto_backups_dir(workspace_root: Path) -> Path:
    """Path to the encrypted scheduled-backup folder under the workspace root."""
    return Path(workspace_root) / "AutoBackups"


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


def prune_old_backups(backup_dir: Path, keep: int = AUTO_BACKUP_KEEP) -> int:
    """Delete oldest SkyAdminPro_AutoBackup_*.skybackup files, keeping `keep` newest."""
    try:
        candidates = sorted(backup_dir.glob("SkyAdminPro_AutoBackup_*.skybackup"))
    except OSError:
        logger.warning("Could not list auto-backup dir: %s", backup_dir)
        return 0
    removed = 0
    for old in candidates[:-keep] if len(candidates) > keep else []:
        try:
            old.unlink()
            removed += 1
        except OSError:
            logger.warning("Could not delete old auto-backup: %s", old)
    return removed


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
        pruned = prune_old_backups(backup_dir)
        if pruned:
            logger.info("Pruned %d old auto-backup(s), keeping %d", pruned, AUTO_BACKUP_KEEP)
        return dest
    except (
        OSError,
        ValueError,
        sqlite3.Error,
    ):  # defensive: crypto+file pipeline — one failure surfaces as a failed backup (logged)
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
