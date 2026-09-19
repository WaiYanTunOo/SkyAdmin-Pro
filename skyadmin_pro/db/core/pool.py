"""Database Core operations."""

from __future__ import annotations

import threading

from skyadmin_pro.db.cipher import (
    DBConnection,
)


class PoolMixin:
    def _get_pooled_conn(self) -> DBConnection:
        """Return the reused connection for the calling thread.

        Main thread uses the historic ``_pooled_conn``; any other thread
        uses its own thread-local handle. Validates liveness first.
        """
        if getattr(self, "_restore_lockout", False):
            raise RuntimeError("Database is locked for restore — reopen the app after restore finishes.")
        if threading.get_ident() == getattr(self, "_main_ident", threading.get_ident()):
            with self._lock:
                conn = self._pooled_conn
                if conn is not None and self._validate_conn(conn):
                    return conn
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:  # defensive: close is best-effort cleanup on a stale handle
                        pass
                    self._pooled_conn = None
                conn = self._connect()
                self._pooled_conn = conn
                return conn
        return self._get_bg_conn()

    def _bundle_active(self) -> bool:
        """True when the calling thread holds a pinned bundle connection."""
        if getattr(self._local, "bundle_conn", None) is not None:
            return True
        return self._bundle_conn is not None and self._bundle_owner == threading.get_ident()

    def _bundle_conn_for_thread(self) -> DBConnection | None:
        conn = getattr(self._local, "bundle_conn", None)
        if conn is not None:
            return conn
        if self._bundle_active():
            return self._bundle_conn
        return None
