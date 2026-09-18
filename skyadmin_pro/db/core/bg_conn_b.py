"""Database Core operations."""

from __future__ import annotations

from skyadmin_pro.db.cipher import (
    DBConnection,
)


class BgConnMixinB:
    def _get_bg_conn_impl(self, *, _depth: int) -> DBConnection:
        conn = getattr(self._local, "conn", None)
        with self._lock:
            epoch = self._pool_epoch
        if conn is not None and getattr(self._local, "conn_epoch", None) == epoch and self._validate_conn(conn):
            return conn
        if conn is not None:
            try:
                conn.close()
            except Exception:  # defensive: close is best-effort cleanup on a stale handle
                pass
            with self._lock:
                try:
                    self._bg_conns.remove(conn)
                except ValueError:
                    pass
            self._local.conn = None
        conn = self._connect()
        self._local.conn = conn
        with self._lock:
            self._local.conn_epoch = self._pool_epoch
        self._track_bg_conn(conn)
        if getattr(self._local, "conn", None) is not conn:
            # Lost a race with _close_pooled_conn (epoch moved) — retry
            # once.  A second failure means something is deeply wrong; raise
            # instead of recursing infinitely.
            if _depth >= 2:
                raise RuntimeError("Failed to acquire background DB connection after retries")
            return self._get_bg_conn_impl(_depth=_depth + 1)
        return conn
