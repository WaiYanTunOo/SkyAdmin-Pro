"""Apply client/supplier/task global_id remaps when writing a remote sync row."""

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

from .chunk_2 import _client_id_for_global
from .fk_lookup import supplier_id_for_global, task_id_for_global


def remap_pull_fks(db, table: str, row: dict[str, Any]) -> None:
    if table in CLIENT_FK_TABLES:
        client_gid = row.pop(FK_CLIENT_COLUMN, None) or row.pop("client_global_id", None)
        row["client_id"] = _client_id_for_global(db, str(client_gid) if client_gid else None)
    if table in SUPPLIER_FK_TABLES:
        supplier_gid = row.pop(FK_SUPPLIER_COLUMN, None) or row.pop("supplier_global_id", None)
        row["supplier_id"] = supplier_id_for_global(db, str(supplier_gid) if supplier_gid else None)
    if table in TASK_FK_TABLES:
        task_gid = row.pop(FK_TASK_COLUMN, None) or row.pop("task_global_id", None)
        row["task_id"] = task_id_for_global(db, str(task_gid) if task_gid else None)
