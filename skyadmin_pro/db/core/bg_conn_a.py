"""Database Core operations."""

from __future__ import annotations

from skyadmin_pro.db.cipher import (
    OPERATIONAL_ERRORS,
    DBConnection,
)


class BgConnMixinA:
    def _validate_conn(self, conn: DBConnection) -> bool:
        try:
            conn.execute("SELECT 1")
            return True
        except OPERATIONAL_ERRORS:
            return False

    def _track_bg_conn(self, conn: DBConnection) -> None:
        with self._lock:
            if getattr(self._local, "conn_epoch", None) != self._pool_epoch:
                # Handle created before a close/restore — drop it instead of
                # re-adding a stale connection to the fresh pool.
                if getattr(self._local, "conn", None) is conn:
                    self._local.conn = None
                try:
                    conn.close()
                except Exception:  # defensive: close is best-effort cleanup on a stale pool handle
                    pass
                return
            if conn not in self._bg_conns:
                self._bg_conns.append(conn)

    def _get_bg_conn(self) -> DBConnection:
        """Per-background-thread pooled handle (never shares main's handle)."""
        return self._get_bg_conn_impl(_depth=0)
