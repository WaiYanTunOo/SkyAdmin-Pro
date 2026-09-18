from __future__ import annotations

import sqlite3

from ._const_4 import CipherOperationalError

OPERATIONAL_ERRORS: tuple[type[BaseException], ...] = (
    sqlite3.OperationalError,
    CipherOperationalError,
)
