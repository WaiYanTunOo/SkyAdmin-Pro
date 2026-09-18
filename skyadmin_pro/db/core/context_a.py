"""Database Core operations."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from skyadmin_pro.db.cipher import (
    DBConnection,
)


class ContextMixinA:
    @contextmanager
    def connection(self) -> Generator[DBConnection, None, None]:
        # Inside a bundle_queries() block on this thread, reuse the pinned
        # handle with no per-checkout validation or intermediate commits.
        pinned = self._bundle_conn_for_thread()
        if pinned is not None:
            yield pinned
            return
        conn = self._get_pooled_conn()
        try:
            yield conn
            conn.commit()
        except Exception:  # defensive: caller body may raise anything — always roll back, then re-raise
            conn.rollback()
            raise

    @contextmanager
    def read_connection(self) -> Generator[DBConnection, None, None]:
        """Pooled checkout for reads — yields a connection WITHOUT committing.

        Inside a bundle_queries() block the pinned handle is reused (the
        bundle owns the commit). Otherwise a pooled handle is yielded with no
        commit on exit (rollback only to reset after an error), avoiding WAL
        write churn from pure SELECTs.
        """
        pinned = self._bundle_conn_for_thread()
        if pinned is not None:
            yield pinned
            return
        conn = self._get_pooled_conn()
        try:
            yield conn
        except Exception:  # defensive: caller body may raise anything — roll back to reset, then re-raise
            try:
                conn.rollback()
            except Exception:  # defensive: rollback itself failed — connection is dead, nothing more to do
                pass
            raise
