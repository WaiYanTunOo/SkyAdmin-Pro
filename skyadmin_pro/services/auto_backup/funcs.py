from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from ._const_0 import logger
from ._const_4 import AUTO_BACKUP_KEEP


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
