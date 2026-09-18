"""Database Core operations."""

from __future__ import annotations


class ShutdownMixin:
    def shutdown(self) -> None:
        """Fold the WAL back into the main file and update query planner stats.

        Call once when the app closes so backups/portable copies are
        self-contained single files.
        """
        try:
            with self.connection() as conn:
                conn.execute("PRAGMA optimize")
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            self._log.warning("Shutdown checkpoint failed", exc_info=True)
        finally:
            self._close_pooled_conn()

    def _close_pooled_conn(self) -> None:
        """Close the pooled connection(s) if open (main + background)."""
        with self._lock:
            conn = self._pooled_conn
            self._pooled_conn = None
            bg = list(self._bg_conns)
            self._bg_conns.clear()
            self._bundle_conn = None
            self._bundle_owner = None
            self._bundle_depth = 0
            self._pool_epoch += 1
            # Close while holding the lock so a background thread cannot
            # _track_bg_conn() a pre-close handle back into the fresh pool.
            # (Stale thread-local handles are additionally rejected by the
            # epoch check in _track_bg_conn/_get_bg_conn.)
            for c in ([conn] if conn is not None else []) + bg:
                try:
                    c.close()
                except Exception:
                    pass
        for attr in ("conn", "bundle_conn", "bundle_depth"):
            try:
                delattr(self._local, attr)
            except AttributeError:
                pass
