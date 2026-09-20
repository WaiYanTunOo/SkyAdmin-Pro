"""Migration 021 — drop redundant idx_clients_name index.

clients.name is `NOT NULL UNIQUE COLLATE NOCASE`, so SQLite auto-creates a
covering NOCASE index (sqlite_autoindex_clients_1) for it. Every name lookup
uses COLLATE NOCASE, so the explicit binary-collation idx_clients_name was
never selected (verified via EXPLAIN QUERY PLAN and a repo grep for
`COLLATE BINARY` usages). Remove it from existing databases; fresh installs
get it from base schema automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 21
NAME = "drop_redundant_idx_clients_name"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        conn.execute("DROP INDEX IF EXISTS idx_clients_name")
