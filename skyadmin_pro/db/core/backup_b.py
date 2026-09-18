"""Database Core operations."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from skyadmin_pro.db.cipher import (
    migrate_plaintext_to_cipher,
)
from skyadmin_pro.paths import remove_sqlite_sidecars


class BackupMixinB:
    def restore_backup(self, backup_path: Path) -> bool:
        """Restore the database from a backup file.

        Creates a safety backup of the current database before restoring.
        Returns True if restore was successful, False otherwise.
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            self._log.error("Backup file not found: %s", backup_path)
            return False

        # Create safety backup of current state
        safety_backup = self.db_file.parent / "backups" / f"skyadmin_pro_pre_restore_{date.today().isoformat()}.db"
        try:
            self.backup_to(safety_backup)
        except Exception:
            self._log.warning("Could not create safety backup", exc_info=True)

        try:
            # Verify backup integrity before restoring (keyed open: a backup
            # encrypted with a different key fails here, not after the swap).
            from skyadmin_pro.db import cipher as _cipher

            conn = _cipher.connect(str(backup_path))
            try:
                result = conn.execute("PRAGMA quick_check").fetchone()
                if result[0] != "ok":
                    self._log.error("Backup file integrity check failed")
                    return False
            finally:
                conn.close()

            # Close pooled/WAL handles BEFORE overwriting the DB file
            # (Windows file locks + torn WAL if copy happens while open).
            self._close_pooled_conn()
            self._wal_enabled = None

            # Copy backup to current database location, then upgrade legacy
            # plaintext backups so the live file is always cipher.
            import shutil

            shutil.copy2(str(backup_path), str(self.db_file))
            migrate_plaintext_to_cipher(self.db_file)
            remove_sqlite_sidecars(self.db_file)

            # Reinitialize with the restored database
            self._client_names_cache = None
            self._service_types_cache = None
            self._initialize()
            self._log.info("Database restored from %s", backup_path)
            return True
        except Exception:
            self._log.exception("Failed to restore backup")
            return False
