"""Build a filtered sync push payload with FK remaps (single-row path)."""

from __future__ import annotations

from typing import Any

from skyadmin_pro.services.sync_schema import (
    CLIENT_FK_TABLES,
    FK_CLIENT_COLUMN,
    FK_GROUP_COLUMN,
    FK_SUPPLIER_COLUMN,
    FK_TASK_COLUMN,
    SUPPLIER_FK_TABLES,
    SYNC_EXCLUDED_COLUMNS,
    TASK_FK_TABLES,
)

from .chunk_2 import _client_global_id
from .fk_lookup import supplier_global_id, task_global_id


def row_to_sync_payload(db, table: str, row: dict) -> dict[str, Any]:
    payload = dict(row)
    for col in SYNC_EXCLUDED_COLUMNS.get(table, frozenset()):
        payload.pop(col, None)
    if table in CLIENT_FK_TABLES:
        payload[FK_CLIENT_COLUMN] = _client_global_id(db, row.get("client_id"))
        payload.pop("client_id", None)
    if table in SUPPLIER_FK_TABLES:
        payload[FK_SUPPLIER_COLUMN] = supplier_global_id(db, row.get("supplier_id"))
        payload.pop("supplier_id", None)
    if table in TASK_FK_TABLES:
        payload[FK_TASK_COLUMN] = task_global_id(db, row.get("task_id"))
        payload.pop("task_id", None)
    if table == "clients":
        gid = row.get("group_id")
        if gid is not None:
            g_row = db._fetch_one(
                "SELECT global_id FROM client_groups WHERE id = ? AND deleted_at IS NULL",
                (int(gid),),
            )
            payload[FK_GROUP_COLUMN] = str(g_row["global_id"]) if g_row and g_row.get("global_id") else None
        else:
            payload[FK_GROUP_COLUMN] = None
        payload.pop("group_id", None)
    payload["global_id"] = str(row.get("global_id") or "")
    return payload
