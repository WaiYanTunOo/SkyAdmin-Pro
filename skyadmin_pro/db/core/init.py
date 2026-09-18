"""Database Core operations."""

from __future__ import annotations

from skyadmin_pro.db.schema import SCHEMA_SQL


class InitMixin:
    def _initialize(self) -> None:
        from skyadmin_pro.db.migrations import run_pending_migrations

        run_pending_migrations(self, max_version=1)
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)
        run_pending_migrations(self, min_version=2)
        self._seed_settings()
        self._seed_checklist_templates()
        self._seed_pricing_matrix()
        # Safety net: verify integrity once, then take today's snapshot.
        ok = True
        try:
            ok = self.quick_check()
        except Exception:
            self._log.warning("Integrity check failed", exc_info=True)
            ok = False
        if not ok:
            # Persist flag for UI banner (Settings will surface)
            try:
                self.set_setting("db_integrity_failed", "1")
            except Exception:
                self._log.debug("Could not set db_integrity_failed flag", exc_info=True)
            self._log.error("DB integrity FAILED — UI should show banner; restore from backups if needed")
        else:
            try:
                self.set_setting("db_integrity_failed", "0")
            except Exception:
                self._log.debug("Could not clear db_integrity_failed flag", exc_info=True)
        try:
            self.auto_backup()
        except Exception:
            # Startup must never block or crash because of backups.
            self._log.warning("Auto-backup failed", exc_info=True)
