from __future__ import annotations

from skyadmin_pro.services.sync_schema import FK_SUPPLIER_COLUMN, FK_TASK_COLUMN

from ..importer.funcs import Database
from ._common import (
    FK_CLIENT_COLUMN,
    FK_GROUP_COLUMN,
    SYNC_ALLOWED_COLUMNS,
    SYNC_EXCLUDED_COLUMNS,
    SYNC_PUSH_ORDER,
    SYNC_PUSH_PAGE_SIZE,
    Any,
    hlc_now,
)
from .chunk_3 import _filter_sync_row, _sync_ident
from .cred_payload import apply_vault_secret_for_push
from .fk_push import remap_push_fks
from .gid_maps import load_gid_maps

_META = (
    "global_id",
    "created_at",
    "updated_at",
    "deleted_at",
    "hlc",
    FK_CLIENT_COLUMN,
    FK_GROUP_COLUMN,
    FK_SUPPLIER_COLUMN,
    FK_TASK_COLUMN,
)


def collect_local_changes(db: Database, *, since: str = "", limit: int | None = None) -> list[dict[str, Any]]:
    """Collect active rows and soft-delete tombstones for push (bounded globally)."""
    if limit is None:
        limit = SYNC_PUSH_PAGE_SIZE
    changes: list[dict[str, Any]] = []
    since = (since or "").strip()
    client_m, group_m, supplier_m, task_m = load_gid_maps(db)
    vault_passwords = False
    for table in SYNC_PUSH_ORDER:
        t = _sync_ident(table)
        q = f"SELECT * FROM {t} WHERE global_id IS NOT NULL AND TRIM(global_id) != ''" + (
            " AND updated_at > ? ORDER BY updated_at ASC LIMIT ?" if since else " ORDER BY updated_at ASC LIMIT ?"
        )
        rows = db._fetch_all(q, (since, limit) if since else (limit,))
        for row in rows:
            deleted_at = row.get("deleted_at")
            if deleted_at:
                row_payload = {"global_id": str(row["global_id"])}
            else:
                payload = dict(row)
                for col in SYNC_EXCLUDED_COLUMNS.get(table, frozenset()):
                    payload.pop(col, None)
                remap_push_fks(
                    table,
                    payload,
                    row,
                    client_gid_map=client_m,
                    supplier_gid_map=supplier_m,
                    task_gid_map=task_m,
                )
                if table == "office_credentials":
                    payload.pop("contact_id", None)
                if table == "clients":
                    local_gid = row.get("group_id")
                    payload[FK_GROUP_COLUMN] = group_m.get(int(local_gid)) if local_gid is not None else None
                    payload.pop("group_id", None)
                payload = {
                    k: v for k, v in payload.items() if k in SYNC_ALLOWED_COLUMNS.get(table, frozenset()) or k in _META
                }
                payload["global_id"] = str(row.get("global_id") or "")
                payload, included = apply_vault_secret_for_push(db, table, payload)
                vault_passwords = vault_passwords or included
                row_payload = _filter_sync_row(table, payload)
                row_payload["global_id"] = str(row["global_id"])
            changes.append(
                {
                    "table": table,
                    "global_id": str(row["global_id"]),
                    "row": row_payload,
                    "updated_at": str(row.get("updated_at") or row.get("created_at") or ""),
                    "deleted_at": deleted_at,
                    "proto": 2,
                }
            )
    # Keep updated_at as the primary ordering (push cursor semantics), then stamp
    # HLCs in that final order so collect order always matches HLC order.
    changes.sort(key=lambda c: c["updated_at"])
    for change in changes:
        change["hlc"] = hlc_now(db)
    collect_local_changes.last_vault_passwords = vault_passwords  # type: ignore[attr-defined]
    return changes[:limit]
