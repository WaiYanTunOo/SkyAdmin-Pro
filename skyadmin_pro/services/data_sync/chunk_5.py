from __future__ import annotations

from ..importer.funcs import Database
from ._common import *
from ._common import (
    FK_CLIENT_COLUMN,
    FK_GROUP_COLUMN,
    INTEGRITY_ERRORS,
    SYNC_TABLES,
    Any,
    legacy_hlc,
    note_remote_hlc,
    parse_hlc,
)
from .chunk_2 import _client_id_for_global, _group_id_for_global
from .chunk_3 import _filter_sync_row, _parse_updated_at, _sync_ident, _unique_group_name
from .chunk_4 import log_sync_conflict


def _apply_remote_change(db: Database, change: dict[str, Any]) -> str:
    """Apply one remote change. Returns 'applied', 'skipped', or 'invalid'.

    Phase 2 merge: when both sides carry a valid HLC the clocks decide
    (total order — ties impossible); otherwise the legacy updated_at
    comparison applies. Either way the incoming HLC, when valid, is stored
    and the local clock fast-forwards past it.
    """
    table = str(change.get("table") or "")
    global_id = str(change.get("global_id") or "").strip()
    updated_at = str(change.get("updated_at") or "").strip()
    if table not in SYNC_TABLES or not global_id or (not updated_at):
        return "invalid"
    remote_hlc = parse_hlc(change.get("hlc"))
    local = db._fetch_one(f"SELECT id, updated_at, hlc FROM {_sync_ident(table)} WHERE global_id = ?", (global_id,))
    local_hlc = None
    if local:
        local_hlc = parse_hlc(local.get("hlc")) or legacy_hlc(str(local.get("updated_at") or ""))
    if local and (
        remote_hlc is not None
        and local_hlc is not None
        and (remote_hlc <= local_hlc)
        or (
            (remote_hlc is None or local_hlc is None)
            and _parse_updated_at(str(local.get("updated_at") or "")) >= _parse_updated_at(updated_at)
        )
    ):
        local_hlc_str = local.get("hlc") if isinstance(local.get("hlc"), str) else None
        log_sync_conflict(
            db,
            table=table,
            global_id=global_id,
            direction="pull",
            local_updated_at=str(local.get("updated_at") or ""),
            remote_updated_at=updated_at,
            hlc_winner=local_hlc_str,
            hlc_loser=str(change.get("hlc") or ""),
        )
        if remote_hlc is not None:
            note_remote_hlc(db, change.get("hlc"))
        return "skipped"
    if remote_hlc is not None:
        note_remote_hlc(db, change.get("hlc"))
    if change.get("deleted_at"):
        if local:
            t = _sync_ident(table)
            with db.connection() as conn:
                if remote_hlc is not None:
                    conn.execute(
                        f"UPDATE {t} SET deleted_at = ?, updated_at = ?, hlc = ? WHERE global_id = ?",
                        (change.get("deleted_at"), updated_at, str(change.get("hlc")), global_id),
                    )
                else:
                    conn.execute(
                        f"UPDATE {t} SET deleted_at = ?, updated_at = ? WHERE global_id = ?",
                        (change.get("deleted_at"), updated_at, global_id),
                    )
            if table == "client_groups":
                local_id = int(local["id"])
                with db.connection() as conn:
                    conn.execute("UPDATE clients SET group_id = NULL WHERE group_id = ?", (local_id,))
        return "applied"
    row = _filter_sync_row(table, dict(change.get("row") or {}))
    row["global_id"] = global_id
    row["updated_at"] = updated_at
    row.pop("deleted_at", None)
    if remote_hlc is not None:
        row["hlc"] = str(change.get("hlc"))
    if table in ("tasks", "office_contacts", "notebook_entries"):
        client_gid = row.pop(FK_CLIENT_COLUMN, None) or row.pop("client_global_id", None)
        row["client_id"] = _client_id_for_global(db, str(client_gid) if client_gid else None)
    if table == "clients":
        group_gid = row.pop(FK_GROUP_COLUMN, None) or row.pop("group_global_id", None)
        row.pop("group_id", None)
        row["group_id"] = _group_id_for_global(db, str(group_gid) if group_gid else None)
    if table == "client_groups" and "name" in row:
        row["name"] = _unique_group_name(db, str(row.get("name") or ""), global_id)
    if not row or (len(row) <= 2 and (not change.get("deleted_at"))):
        return "invalid"
    if local:
        cols = [k for k in row if k != "global_id"]
        if not cols:
            return "invalid"
        assignments = ", ".join(f"{_sync_ident(col)} = ?" for col in cols)
        values = [row[col] for col in cols] + [global_id]
        with db.connection() as conn:
            conn.execute(f"UPDATE {_sync_ident(table)} SET {assignments} WHERE global_id = ?", values)
        return "applied"
    cols = list(row.keys())
    col_list = ", ".join(_sync_ident(c) for c in cols)
    placeholders = ", ".join("?" for _ in cols)
    try:
        with db.connection() as conn:
            conn.execute(
                f"INSERT INTO {_sync_ident(table)} ({col_list}) VALUES ({placeholders})", [row[col] for col in cols]
            )
    except INTEGRITY_ERRORS:
        if table != "client_groups" or "name" not in row:
            raise
        row["name"] = _unique_group_name(db, f"{row.get('name')}*", global_id)
        with db.connection() as conn:
            conn.execute(
                f"INSERT INTO {_sync_ident(table)} ({col_list}) VALUES ({placeholders})", [row[col] for col in cols]
            )
    return "applied"
