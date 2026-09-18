from __future__ import annotations

from ..importer.funcs import Database
from ._common import (
    SYNC_TABLES,
    Any,
    legacy_hlc,
    note_remote_hlc,
    parse_hlc,
)
from .chunk_3 import _parse_updated_at, _sync_ident
from .chunk_4 import log_sync_conflict
from .chunk_5_write import _apply_remote_delete, _apply_remote_upsert


def _apply_remote_change(db: Database, change: dict[str, Any]) -> str:
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
        return _apply_remote_delete(db, table, local, change, updated_at, global_id, remote_hlc)
    return _apply_remote_upsert(db, table, local, change, updated_at, global_id, remote_hlc)
