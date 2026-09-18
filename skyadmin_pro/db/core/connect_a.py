"""Database Core operations."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from skyadmin_pro.db.cipher import (
    DBConnection,
    migrate_plaintext_to_cipher,
)
from skyadmin_pro.paths import database_path


class ConnectMixinA:
    def __init__(self, db_file: Path | None = None) -> None:
        self.db_file = Path(db_file) if db_file else database_path()
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self._log = logging.getLogger(__name__)
        self._service_types_cache: list[str] | None = None
        self._organization_list_cache: list[str] | None = None
        self._department_list_cache: list[str] | None = None
        self._client_names_cache: list[str] | None = None
        self._wal_enabled: bool | None = None
        self._pooled_conn: DBConnection | None = None
        self._bundle_conn: DBConnection | None = None
        self._bundle_owner: int | None = None
        self._bundle_depth: int = 0
        # Thread-safety: one SQLite handle per thread. SQLite connections
        # must not cross threads (check_same_thread). Main thread keeps the
        # historic pooled handle; background threads get their own pooled
        # handle via thread-local storage so run_background() workers are safe.
        self._local = threading.local()
        self._lock = threading.RLock()
        self._main_ident = threading.get_ident()
        self._bg_conns: list[DBConnection] = []
        # Generation epoch: bumped (under _lock) by _close_pooled_conn so a
        # background thread holding a pre-close handle discards it instead of
        # re-adding a stale connection after the close copied the list.
        self._pool_epoch: int = 0
        # Phase 1 (SQLCipher): upgrade a legacy plaintext DB in place before
        # anything opens it. Fail-closed: a broken migration raises with the
        # original file untouched (restore from ~/.skyadmin_pro/backups).
        migrate_plaintext_to_cipher(self.db_file)
        self._initialize()
