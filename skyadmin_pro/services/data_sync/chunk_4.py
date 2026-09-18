from __future__ import annotations

from ..importer.funcs import Database
from ._common import *
from ._common import (
    SETTING_DATA_SYNC_ENABLED,
)


def is_data_sync_enabled(db: Database) -> bool:
    return (db.get_setting(SETTING_DATA_SYNC_ENABLED) or "0").strip() == "1"


def log_sync_conflict(
    db: Database,
    *,
    table: str,
    global_id: str,
    direction: str,
    local_updated_at: str | None,
    remote_updated_at: str | None,
    hlc_winner: str | None = None,
    hlc_loser: str | None = None,
) -> None:
    with db.connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM sync_conflicts WHERE table_name = ? AND global_id = ? AND direction = ? LIMIT 1",
            (table, global_id, direction),
        ).fetchone()
        if existing:
            return
        conn.execute(
            "INSERT INTO sync_conflicts (table_name, global_id, direction, local_updated_at, remote_updated_at, hlc_winner, hlc_loser) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (table, global_id, direction, local_updated_at, remote_updated_at, hlc_winner, hlc_loser),
        )
