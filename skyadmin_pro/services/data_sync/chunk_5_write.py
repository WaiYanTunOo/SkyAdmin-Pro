from __future__ import annotations

from skyadmin_pro.services.mobile_vault import VAULT_SYNC_TABLES

from ._common import FK_GROUP_COLUMN, INTEGRITY_ERRORS
from .chunk_2 import _group_id_for_global
from .chunk_3 import _filter_sync_row, _sync_ident, _unique_group_name
from .cred_payload import strip_mobile_secret_on_pull
from .fk_pull import remap_pull_fks


def _apply_remote_delete(db, table, local, change, updated_at, global_id, remote_hlc) -> str:
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


def _apply_remote_upsert(db, table, local, change, updated_at, global_id, remote_hlc) -> str:
    row = strip_mobile_secret_on_pull(table, _filter_sync_row(table, dict(change.get("row") or {})))
    row["global_id"] = global_id
    row["updated_at"] = updated_at
    row.pop("deleted_at", None)
    if remote_hlc is not None:
        row["hlc"] = str(change.get("hlc"))
    remap_pull_fks(db, table, row)
    if table == "clients":
        group_gid = row.pop(FK_GROUP_COLUMN, None) or row.pop("group_global_id", None)
        row.pop("group_id", None)
        row["group_id"] = _group_id_for_global(db, str(group_gid) if group_gid else None)
    if table == "client_groups" and "name" in row:
        row["name"] = _unique_group_name(db, str(row.get("name") or ""), global_id)
    if table in VAULT_SYNC_TABLES and not local:
        row.setdefault("secret_value", "")
        if table == "client_credentials" and row.get("client_id") is None:
            return "invalid"
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
                f"INSERT INTO {_sync_ident(table)} ({col_list}) VALUES ({placeholders})",
                [row[col] for col in cols],
            )
    except INTEGRITY_ERRORS:
        if table != "client_groups" or "name" not in row:
            raise
        row["name"] = _unique_group_name(db, f"{row.get('name')}*", global_id)
        with db.connection() as conn:
            conn.execute(
                f"INSERT INTO {_sync_ident(table)} ({col_list}) VALUES ({placeholders})",
                [row[col] for col in cols],
            )
    return "applied"
