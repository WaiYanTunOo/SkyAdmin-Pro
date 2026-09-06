"""Migration 010 — rebuild clients_fts from the clients table.

Self-heal for legacy databases whose FTS index exists but went stale
(e.g. triggers were ever missing): wipe and repopulate from source.
Triggers are dropped during the refill and re-created after, mirroring
the _backfill_sync_global_ids pattern. Cheap at any realistic row count.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 10
NAME = "fts_rebuild"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    # Local import: core imports this package inside _initialize.
    from skyadmin_pro.db.core import CoreMixin

    with db.connection() as conn:
        has_fts = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'clients_fts'").fetchone()
        if not has_fts:
            return
        CoreMixin._drop_clients_fts_triggers(conn)
        conn.execute("DELETE FROM clients_fts")
        conn.execute(
            """
            INSERT INTO clients_fts(rowid, name, contact_name, email)
            SELECT id, COALESCE(name, ''), COALESCE(contact_name, ''), COALESCE(email, '')
            FROM clients
            """
        )
        CoreMixin._ensure_clients_fts_triggers(conn)
