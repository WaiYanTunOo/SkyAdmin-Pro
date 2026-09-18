from __future__ import annotations

from ..importer.funcs import Database
from ._common import *
from ._common import (
    DB_ERRORS,
    FK_CLIENT_COLUMN,
    FK_GROUP_COLUMN,
    SETTING_DATA_SYNC_ENABLED,
    SYNC_ALLOWED_COLUMNS,
    SYNC_EXCLUDED_COLUMNS,
    SYNC_PUSH_ORDER,
    SYNC_PUSH_PAGE_SIZE,
    Any,
    hlc_now,
    logger,
)
from .chunk_3 import _filter_sync_row, _sync_ident


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
            "\n            SELECT 1 FROM sync_conflicts\n            WHERE table_name = ? AND global_id = ? AND direction = ?\n            LIMIT 1\n            ",
            (table, global_id, direction),
        ).fetchone()
        if existing:
            return
        conn.execute(
            "\n            INSERT INTO sync_conflicts (table_name, global_id, direction, local_updated_at, remote_updated_at,\n                                        hlc_winner, hlc_loser)\n            VALUES (?, ?, ?, ?, ?, ?, ?)\n            ",
            (table, global_id, direction, local_updated_at, remote_updated_at, hlc_winner, hlc_loser),
        )


def collect_local_changes(db: Database, *, since: str = "", limit: int | None = None) -> list[dict[str, Any]]:
    """Collect active rows and soft-delete tombstones for push (bounded globally)."""
    if limit is None:
        limit = SYNC_PUSH_PAGE_SIZE
    changes: list[dict[str, Any]] = []
    since = (since or "").strip()
    client_gid_map: dict[int, str | None] = {}
    group_gid_map: dict[int, str | None] = {}
    try:
        for row in db._fetch_all("SELECT id, global_id FROM clients"):
            client_gid_map[int(row["id"])] = str(row["global_id"]) if row.get("global_id") else None
    except DB_ERRORS:
        logger.warning("Batch client GID lookup failed, using per-row fallback", exc_info=True)
        client_gid_map = {}
    try:
        for row in db._fetch_all("SELECT id, global_id FROM client_groups WHERE deleted_at IS NULL"):
            group_gid_map[int(row["id"])] = str(row["global_id"]) if row.get("global_id") else None
    except DB_ERRORS:
        logger.warning("Batch group GID lookup failed, using per-row fallback", exc_info=True)
        group_gid_map = {}
    for table in SYNC_PUSH_ORDER:
        t = _sync_ident(table)
        if since:
            rows = db._fetch_all(
                f"\n                SELECT * FROM {t}\n                WHERE global_id IS NOT NULL AND TRIM(global_id) != ''\n                  AND updated_at > ?\n                ORDER BY updated_at ASC LIMIT ?\n                ",
                (since, limit),
            )
        else:
            rows = db._fetch_all(
                f"SELECT * FROM {t} WHERE global_id IS NOT NULL AND TRIM(global_id) != '' ORDER BY updated_at ASC LIMIT ?",
                (limit,),
            )
        for row in rows:
            deleted_at = row.get("deleted_at")
            if deleted_at:
                row_payload = {"global_id": str(row["global_id"])}
            else:
                payload = dict(row)
                for col in SYNC_EXCLUDED_COLUMNS.get(table, frozenset()):
                    payload.pop(col, None)
                if table in ("tasks", "office_contacts", "notebook_entries"):
                    cid = row.get("client_id")
                    gid = client_gid_map.get(int(cid)) if cid is not None else None
                    payload[FK_CLIENT_COLUMN] = gid
                    payload.pop("client_id", None)
                if table == "clients":
                    local_gid = row.get("group_id")
                    payload[FK_GROUP_COLUMN] = group_gid_map.get(int(local_gid)) if local_gid is not None else None
                    payload.pop("group_id", None)
                payload = {
                    k: v
                    for k, v in payload.items()
                    if k in SYNC_ALLOWED_COLUMNS.get(table, frozenset())
                    or k
                    in ("global_id", "created_at", "updated_at", "deleted_at", "hlc", FK_CLIENT_COLUMN, FK_GROUP_COLUMN)
                }
                payload["global_id"] = str(row.get("global_id") or "")
                row_payload = _filter_sync_row(table, payload)
                row_payload["global_id"] = str(row["global_id"])
            changes.append(
                {
                    "table": table,
                    "global_id": str(row["global_id"]),
                    "row": row_payload,
                    "updated_at": str(row.get("updated_at") or row.get("created_at") or ""),
                    "deleted_at": deleted_at,
                    "hlc": hlc_now(db),
                    "proto": 2,
                }
            )
    changes.sort(key=lambda c: (c["updated_at"], c.get("hlc") or ""))
    return changes[:limit]
