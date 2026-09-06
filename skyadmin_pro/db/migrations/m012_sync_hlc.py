"""Migration 012 — HLC clocks for CRDT merge (Phase 2).

Adds ``hlc TEXT`` to every sync table plus winner/loser clocks on the
merge log (``sync_conflicts``). Existing rows keep NULL hlc and are
ordered by the legacy ``updated_at`` synthesis (see sync_hlc.legacy_hlc).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Mirrors services.sync_schema.SYNC_TABLES (kept inline: db/migrations must
# not import the services package — services/__init__ may pull db back in).
SYNC_TABLES: tuple[str, ...] = (
    "client_groups",
    "clients",
    "tasks",
    "office_contacts",
    "notebook_entries",
)

VERSION = 12
NAME = "sync_hlc"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        for table in SYNC_TABLES:
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "hlc" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN hlc TEXT")
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sync_conflicts)").fetchall()}
        if "hlc_winner" not in cols:
            conn.execute("ALTER TABLE sync_conflicts ADD COLUMN hlc_winner TEXT")
        if "hlc_loser" not in cols:
            conn.execute("ALTER TABLE sync_conflicts ADD COLUMN hlc_loser TEXT")
