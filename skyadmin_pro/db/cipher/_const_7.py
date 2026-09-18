from __future__ import annotations

import sqlite3

from ._const_4 import CipherIntegrityError

INTEGRITY_ERRORS: tuple[type[BaseException], ...] = (
    sqlite3.IntegrityError,
    CipherIntegrityError,
)
