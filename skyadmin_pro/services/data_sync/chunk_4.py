from __future__ import annotations

from ..importer.funcs import Database
from ._common import *
from ._common import (
    SETTING_DATA_SYNC_ENABLED,
)


def is_data_sync_enabled(db: Database) -> bool:
    """User preference AND Worker sync SKU (when claim is present)."""
    if (db.get_setting(SETTING_DATA_SYNC_ENABLED) or "0").strip() != "1":
        return False
    from skyadmin_pro.services.drive.entitlement import license_allows_sync

    return license_allows_sync(db)


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
    actor_winner: str | None = None,
    actor_loser: str | None = None,
    org_id: str | None = None,
) -> None:
    from skyadmin_pro.services.sync_hlc import hlc_actor

    win_actor = (actor_winner or hlc_actor(hlc_winner) or "").strip() or None
    lose_actor = (actor_loser or hlc_actor(hlc_loser) or "").strip() or None
    oid = (org_id or "").strip() or None
    if oid is None:
        try:
            from skyadmin_pro.services.drive.entitlement import license_org_id

            oid = license_org_id(db) or None
        except Exception:
            oid = None
    with db.connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM sync_conflicts WHERE table_name = ? AND global_id = ? AND direction = ? LIMIT 1",
            (table, global_id, direction),
        ).fetchone()
        if existing:
            return
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sync_conflicts)").fetchall()}
        if {"actor_winner", "actor_loser", "org_id"} <= cols:
            conn.execute(
                """
                INSERT INTO sync_conflicts (
                    table_name, global_id, direction, local_updated_at, remote_updated_at,
                    hlc_winner, hlc_loser, actor_winner, actor_loser, org_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    table,
                    global_id,
                    direction,
                    local_updated_at,
                    remote_updated_at,
                    hlc_winner,
                    hlc_loser,
                    win_actor,
                    lose_actor,
                    oid,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO sync_conflicts (
                    table_name, global_id, direction, local_updated_at, remote_updated_at,
                    hlc_winner, hlc_loser
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (table, global_id, direction, local_updated_at, remote_updated_at, hlc_winner, hlc_loser),
            )
