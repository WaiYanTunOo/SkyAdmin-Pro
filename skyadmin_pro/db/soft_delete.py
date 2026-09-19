"""Soft-delete helpers for sync-backed tables (tombstone via deleted_at)."""

from __future__ import annotations

_TABLES = frozenset(
    {
        "clients",
        "suppliers",
        "supplier_payments",
        "supplier_services",
        "pipeline_items",
        "courier_logs",
        "tasks",
        "documents",
        "financial_documents",
        "client_credentials",
        "office_credentials",
        "office_contacts",
        "notebook_entries",
        "renewal_items",
        "client_months",
        "tax_cycle_log",
        "recurring_tasks",
        "appointments",
    }
)

_FK_COLS = frozenset({"supplier_id", "pipeline_item_id", "source_document_id", "client_id"})


def soft_delete_by_id(conn, table: str, row_id: int, now: str) -> int:
    if table not in _TABLES:
        raise ValueError(f"soft_delete_by_id: unsafe table {table!r}")

    cur = conn.execute(
        f"UPDATE {table} SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
        (now, now, row_id),
    )

    return int(cur.rowcount)


def soft_delete_ids(conn, table: str, ids: list[int], now: str) -> int:
    if table not in _TABLES:
        raise ValueError(f"soft_delete_ids: unsafe table {table!r}")

    if not ids:
        return 0

    placeholders = ", ".join("?" for _ in ids)

    cur = conn.execute(
        f"UPDATE {table} SET deleted_at = ?, updated_at = ? WHERE id IN ({placeholders}) AND deleted_at IS NULL",
        (now, now, *ids),
    )

    return int(cur.rowcount)


def soft_delete_by_fk(conn, table: str, fk_col: str, fk_id: int, now: str) -> int:
    if table not in _TABLES or fk_col not in _FK_COLS:
        raise ValueError("soft_delete_by_fk: unsafe ident")

    cur = conn.execute(
        f"UPDATE {table} SET deleted_at = ?, updated_at = ? WHERE {fk_col} = ? AND deleted_at IS NULL",
        (now, now, fk_id),
    )

    return int(cur.rowcount)


def soft_delete_by_fk_ids(conn, table: str, fk_col: str, fk_ids: list[int], now: str) -> int:
    if table not in _TABLES or fk_col not in _FK_COLS:
        raise ValueError("soft_delete_by_fk_ids: unsafe ident")

    if not fk_ids:
        return 0

    ph = ", ".join("?" for _ in fk_ids)

    cur = conn.execute(
        f"UPDATE {table} SET deleted_at = ?, updated_at = ? WHERE {fk_col} IN ({ph}) AND deleted_at IS NULL",
        (now, now, *fk_ids),
    )

    return int(cur.rowcount)
