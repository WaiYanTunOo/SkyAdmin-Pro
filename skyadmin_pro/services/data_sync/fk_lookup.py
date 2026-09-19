"""Resolve local ids ↔ global_ids for sync FK remaps."""

from __future__ import annotations

from ..importer.funcs import Database


def supplier_global_id(db: Database, supplier_id: int | None) -> str | None:
    if not supplier_id:
        return None
    row = db._fetch_one("SELECT global_id FROM suppliers WHERE id = ?", (int(supplier_id),))
    return str(row["global_id"]) if row and row.get("global_id") else None


def supplier_id_for_global(db: Database, global_id: str | None) -> int | None:
    if not global_id:
        return None
    row = db._fetch_one("SELECT id FROM suppliers WHERE global_id = ?", (str(global_id),))
    return int(row["id"]) if row else None


def task_global_id(db: Database, task_id: int | None) -> str | None:
    if not task_id:
        return None
    row = db._fetch_one("SELECT global_id FROM tasks WHERE id = ?", (int(task_id),))
    return str(row["global_id"]) if row and row.get("global_id") else None


def task_id_for_global(db: Database, global_id: str | None) -> int | None:
    if not global_id:
        return None
    row = db._fetch_one("SELECT id FROM tasks WHERE global_id = ?", (str(global_id),))
    return int(row["id"]) if row else None
