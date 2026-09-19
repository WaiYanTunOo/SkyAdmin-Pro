"""Apply client/supplier/task global_id remaps on sync push payloads."""

from __future__ import annotations

from typing import Any

from skyadmin_pro.services.sync_schema import (
    CLIENT_FK_TABLES,
    FK_CLIENT_COLUMN,
    FK_SUPPLIER_COLUMN,
    FK_TASK_COLUMN,
    SUPPLIER_FK_TABLES,
    TASK_FK_TABLES,
)


def remap_push_fks(
    table: str,
    payload: dict[str, Any],
    row: dict[str, Any],
    *,
    client_gid_map: dict[int, str | None],
    supplier_gid_map: dict[int, str | None],
    task_gid_map: dict[int, str | None],
) -> None:
    if table in CLIENT_FK_TABLES:
        cid = row.get("client_id")
        payload[FK_CLIENT_COLUMN] = client_gid_map.get(int(cid)) if cid is not None else None
        payload.pop("client_id", None)
    if table in SUPPLIER_FK_TABLES:
        sid = row.get("supplier_id")
        payload[FK_SUPPLIER_COLUMN] = supplier_gid_map.get(int(sid)) if sid is not None else None
        payload.pop("supplier_id", None)
    if table in TASK_FK_TABLES:
        tid = row.get("task_id")
        payload[FK_TASK_COLUMN] = task_gid_map.get(int(tid)) if tid is not None else None
        payload.pop("task_id", None)
