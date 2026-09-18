"""Migration 001 — legacy schema upgrades for pre-release databases.

This is the versioned home of the former CoreMixin._migrate() monolith.
It runs inside one explicit transaction so a crash can never leave a
half-migrated schema. DDL in Python 3.12's sqlite3 autocommits by default,
which is why this uses a dedicated connection with isolation_level=None
and manual BEGIN/COMMIT instead of db.connection().
"""

from __future__ import annotations

from ._const_0 import VERSION
from ._const_1 import NAME
from .funcs import upgrade
