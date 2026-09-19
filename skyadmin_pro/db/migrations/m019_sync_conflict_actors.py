"""Migration 019 — sync conflict audit actors + org_id (Wave 1b)."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 19
NAME = "sync_conflict_actors"

COLUMNS: tuple[tuple[str, str], ...] = (
    ("actor_winner", "actor_winner TEXT"),
    ("actor_loser", "actor_loser TEXT"),
    ("org_id", "org_id TEXT"),
)

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sync_conflicts)").fetchall()}
        for name, ddl in COLUMNS:
            if name not in cols:
                conn.execute(f"ALTER TABLE sync_conflicts ADD COLUMN {ddl}")
