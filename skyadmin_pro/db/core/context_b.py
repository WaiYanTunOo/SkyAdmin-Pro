"""Database Core operations."""

from __future__ import annotations

import threading
from collections.abc import Generator
from contextlib import contextmanager

from skyadmin_pro.db.cipher import (
    DBConnection,
)


class ContextMixinB:
    @contextmanager
    def bundle_queries(self) -> Generator[DBConnection, None, None]:
        """Pin one pooled connection for a batch of queries (e.g. dashboard snapshot).

        Nest-safe per thread: nested connection() checkouts on the same
        thread reuse the pin with one commit on clean exit (rollback on
        error). Each thread pins its *own* handle; a thread that did not
        open the bundle never touches another thread's pin.
        """
        existing = getattr(self._local, "bundle_conn", None)
        if existing is not None:
            self._local.bundle_depth = int(getattr(self._local, "bundle_depth", 1)) + 1
            try:
                yield existing
            finally:
                self._local.bundle_depth -= 1
            return
        # Legacy pin held by a *different* thread — do not touch it.
        if self._bundle_conn is not None and self._bundle_owner != threading.get_ident():
            with self.connection() as conn:
                yield conn
            return
        conn = self._get_pooled_conn()
        self._local.bundle_conn = conn
        self._local.bundle_depth = 1
        is_main = threading.get_ident() == getattr(self, "_main_ident", threading.get_ident())
        if is_main:
            with self._lock:
                self._bundle_conn = conn
                self._bundle_owner = threading.get_ident()
                self._bundle_depth = 1
        try:
            yield conn
            conn.commit()
        except Exception:  # defensive: caller body may raise anything — always roll back, then re-raise
            conn.rollback()
            raise
        finally:
            try:
                delattr(self._local, "bundle_conn")
            except AttributeError:
                pass
            self._local.bundle_depth = 0
            if is_main:
                with self._lock:
                    self._bundle_conn = None
                    self._bundle_owner = None
                    self._bundle_depth = 0
