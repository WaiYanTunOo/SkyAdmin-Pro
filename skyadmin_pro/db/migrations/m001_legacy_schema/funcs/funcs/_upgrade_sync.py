from __future__ import annotations


def _upgrade_sync(conn, existing) -> None:
    from skyadmin_pro.db.core import CoreMixin

    for sync_table in ("clients", "tasks", "office_contacts", "notebook_entries"):
        if sync_table not in existing:
            continue
        sync_cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({sync_table})")}
        if "global_id" not in sync_cols:
            conn.execute(f"ALTER TABLE {sync_table} ADD COLUMN global_id TEXT")
        if "deleted_at" not in sync_cols:
            conn.execute(f"ALTER TABLE {sync_table} ADD COLUMN deleted_at TEXT")
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{sync_table}_global_id "
            f"ON {sync_table}(global_id) WHERE global_id IS NOT NULL"
        )
    if "clients" in existing:
        fts_row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients_fts'").fetchone()
        if not fts_row:
            # NOTE: executescript() implicitly commits on the SQLCipher
            # driver, which would break this migration's single
            # transaction — run the statements discretely instead.
            conn.execute(
                """
                CREATE VIRTUAL TABLE clients_fts USING fts5(
                    name, contact_name, email, tokenize='unicode61'
                )
                """
            )
            conn.execute(
                """
                INSERT INTO clients_fts(rowid, name, contact_name, email)
                SELECT id,
                       COALESCE(name, ''),
                       COALESCE(contact_name, ''),
                       COALESCE(email, '')
                FROM clients
                """
            )
            CoreMixin._ensure_clients_fts_triggers(conn)
        else:
            CoreMixin._ensure_clients_fts_triggers(conn)
