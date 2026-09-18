"""Database Core operations."""

from __future__ import annotations

from datetime import date
from pathlib import Path


class BackupMixinA:
    def quick_check(self) -> bool:
        """Run PRAGMA quick_check; log a loud warning when the DB is suspect."""
        with self.connection() as conn:
            row = conn.execute("PRAGMA quick_check").fetchone()
        ok = bool(row) and row[0] == "ok"
        if not ok:
            self._log.error(
                "Database integrity check FAILED: %s — restore from ~/.skyadmin_pro/backups if data looks wrong.",
                [r[0] for r in self._fetch_all("PRAGMA quick_check")][:5],
            )
        return ok

    def backup_to(self, dest: Path) -> Path:
        """Online-safe snapshot of the live database (includes WAL content)."""
        from skyadmin_pro.db import cipher as _cipher

        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = _cipher.connect(str(self.db_file))
        try:
            out = _cipher.connect(str(dest))
            try:
                src.backup(out)
            finally:
                out.close()
        finally:
            src.close()
        return dest

    def auto_backup(self, keep: int = 7) -> Path | None:
        """One snapshot per day into ~/.skyadmin_pro/backups, keeping `keep`."""
        today = date.today().isoformat()
        if self.get_setting("last_backup_date") == today:
            return None
        d = self.db_file.parent / "backups"
        p = d / f"skyadmin_pro_{today}.db"
        self.backup_to(p)
        self.set_setting("last_backup_date", today)
        for old in sorted(d.glob("skyadmin_pro_*.db"))[:-keep]:
            try:
                old.unlink(missing_ok=True)
            except OSError:
                pass
        return p
