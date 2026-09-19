"""Batch-load id → global_id maps for sync push FK remaps."""

from __future__ import annotations

from ..importer.funcs import Database
from ._common import DB_ERRORS, logger

GidMaps = tuple[
    dict[int, str | None],
    dict[int, str | None],
    dict[int, str | None],
    dict[int, str | None],
]


def load_gid_maps(db: Database) -> GidMaps:
    client_map: dict[int, str | None] = {}
    group_map: dict[int, str | None] = {}
    supplier_map: dict[int, str | None] = {}
    task_map: dict[int, str | None] = {}
    _load(db, "clients", client_map, "Batch client GID lookup failed")
    try:
        for row in db._fetch_all("SELECT id, global_id FROM client_groups WHERE deleted_at IS NULL"):
            group_map[int(row["id"])] = str(row["global_id"]) if row.get("global_id") else None
    except DB_ERRORS:
        logger.warning("Batch group GID lookup failed, using per-row fallback", exc_info=True)
    _load(db, "suppliers", supplier_map, "Batch supplier GID lookup failed")
    _load(db, "tasks", task_map, "Batch task GID lookup failed")
    return client_map, group_map, supplier_map, task_map


def _load(db: Database, table: str, out: dict[int, str | None], warn: str) -> None:
    try:
        for row in db._fetch_all(f"SELECT id, global_id FROM {table}"):
            out[int(row["id"])] = str(row["global_id"]) if row.get("global_id") else None
    except DB_ERRORS:
        logger.warning("%s, using per-row fallback", warn, exc_info=True)
