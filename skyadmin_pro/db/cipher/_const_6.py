from __future__ import annotations

import sqlite3

from ._const_4 import CipherError

DB_ERRORS: tuple[type[BaseException], ...] = (sqlite3.Error, CipherError)
