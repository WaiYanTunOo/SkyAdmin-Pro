"""Database Core operations."""

from __future__ import annotations

from skyadmin_pro.db.cipher import (
    DB_ERRORS,
    CipherError,
    CipherRow,
    DBConnection,
)


class ConnectMixinB:
    def _connect(self) -> DBConnection:
        from skyadmin_pro.db import cipher as _cipher

        conn = _cipher.connect(self.db_file, timeout=10, check_same_thread=False)
        conn.row_factory = CipherRow
        try:
            # Fail-closed key check: PRAGMA key alone never verifies, so the
            # first read proves the key (wrong key / corrupt file raises here,
            # not pages later inside a transaction).
            conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except CipherError as exc:
            conn.close()
            raise RuntimeError(
                "Database key mismatch or corrupt file — restore from "
                f"{self.db_file.parent / 'backups'} if data looks wrong."
            ) from exc
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA cache_size = -8000")
        conn.execute("PRAGMA busy_timeout = 5000")

        wal_setting = True
        try:
            row = conn.execute("SELECT value FROM settings WHERE key = 'db_wal_mode'").fetchone()
            if row and row["value"] == "0":
                wal_setting = False
        except Exception:
            pass

        try:
            if wal_setting:
                cur = conn.execute("PRAGMA journal_mode=WAL")
                mode = cur.fetchone()
                # WAL returns 'wal' on success; log if fallback
                if mode and str(mode[0]).lower() != "wal":
                    self._log.warning("WAL mode not enabled, got %s", mode[0])
                    self._wal_enabled = False
                else:
                    self._wal_enabled = True
            else:
                conn.execute("PRAGMA journal_mode=DELETE")
                self._wal_enabled = False
        except DB_ERRORS:
            self._log.warning("WAL mode unavailable; staying in rollback-journal mode")
            self._wal_enabled = False
        return conn
