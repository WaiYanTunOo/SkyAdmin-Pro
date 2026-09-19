"""Client cascade soft-delete / stamp restore (sync-backed children)."""

from __future__ import annotations

from skyadmin_pro.db.soft_delete import soft_delete_by_fk_ids, soft_delete_ids

_CLIENT_CASCADE = (
    "tasks",
    "pipeline_items",
    "documents",
    "financial_documents",
    "client_credentials",
    "office_contacts",
    "notebook_entries",
    "courier_logs",
    "supplier_payments",
    "renewal_items",
    "client_months",
    "tax_cycle_log",
    "recurring_tasks",
    "appointments",
)


def soft_delete_clients_cascade(conn, client_ids: list[int], now: str) -> int:
    """Tombstone clients and synced children. Returns clients updated."""

    if not client_ids:
        return 0

    ph = ", ".join("?" for _ in client_ids)

    conn.execute(
        f"UPDATE tasks SET deleted_at = ?, updated_at = ?"
        f" WHERE pipeline_item_id IN"
        f" (SELECT id FROM pipeline_items WHERE client_id IN ({ph}))"
        f" AND deleted_at IS NULL",
        (now, now, *client_ids),
    )

    for table in _CLIENT_CASCADE:
        soft_delete_by_fk_ids(conn, table, "client_id", client_ids, now)

    return soft_delete_ids(conn, "clients", client_ids, now)


def restore_clients_cascade(conn, client_ids: list[int], stamp: str, now: str) -> int:
    """Clear tombstones stamped ``stamp`` for clients + cascade children."""

    if not client_ids or not stamp:
        return 0

    ph = ", ".join("?" for _ in client_ids)

    for table in _CLIENT_CASCADE:
        conn.execute(
            f"UPDATE {table} SET deleted_at = NULL, updated_at = ? WHERE client_id IN ({ph}) AND deleted_at = ?",
            (now, *client_ids, stamp),
        )

    conn.execute(
        f"UPDATE tasks SET deleted_at = NULL, updated_at = ?"
        f" WHERE pipeline_item_id IN"
        f" (SELECT id FROM pipeline_items WHERE client_id IN ({ph}))"
        f" AND deleted_at = ?",
        (now, *client_ids, stamp),
    )

    cur = conn.execute(
        f"UPDATE clients SET deleted_at = NULL, updated_at = ? WHERE id IN ({ph}) AND deleted_at = ?",
        (now, *client_ids, stamp),
    )

    return int(cur.rowcount)
