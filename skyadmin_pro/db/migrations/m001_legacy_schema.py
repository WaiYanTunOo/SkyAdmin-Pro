"""Migration 001 — legacy schema upgrades for pre-release databases.

This is the versioned home of the former CoreMixin._migrate() monolith.
It runs inside one explicit transaction so a crash can never leave a
half-migrated schema. DDL in Python 3.12's sqlite3 autocommits by default,
which is why this uses a dedicated connection with isolation_level=None
and manual BEGIN/COMMIT instead of db.connection().
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

VERSION = 1
NAME = "legacy_schema"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    # Local import: core imports this package inside _initialize, so a
    # top-level import would be circular. Only needed for FTS triggers.
    from skyadmin_pro.db.core import CoreMixin

    conn = sqlite3.connect(str(db.db_file), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.isolation_level = None  # manual transaction control
        conn.execute("BEGIN IMMEDIATE")
        existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        # Resume guard: a previous run may have crashed between the RENAME
        # and the copy-back below. Recover instead of losing the data.
        if "renewal_items_old" in existing:
            conn.execute("DROP TABLE IF EXISTS renewal_items")
            conn.execute("ALTER TABLE renewal_items_old RENAME TO renewal_items")
            existing.discard("renewal_items_old")
            existing.add("renewal_items")
        if "documents" in existing:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)")}
            for name, ddl in (
                ("payment_date", "payment_date TEXT"),
                ("progress", "progress TEXT"),
                ("paid", "paid INTEGER NOT NULL DEFAULT 0"),
                ("start_date", "start_date TEXT"),
                ("completed_at", "completed_at TEXT"),
            ):
                if name not in columns:
                    conn.execute(f"ALTER TABLE documents ADD COLUMN {ddl}")
        if "clients" in existing:
            client_columns = {row["name"] for row in conn.execute("PRAGMA table_info(clients)")}
            for name, ddl in (
                ("contact_name", "contact_name TEXT"),
                ("email", "email TEXT"),
                ("status", "status TEXT NOT NULL DEFAULT 'active'"),
                ("registration_number", "registration_number TEXT"),
                ("director", "director TEXT"),
                ("contact_number", "contact_number TEXT"),
                ("registered_capital", "registered_capital TEXT"),
                ("vat_registration", "vat_registration TEXT"),
                ("business_address", "business_address TEXT"),
                ("business_objectives", "business_objectives TEXT"),
                ("tax_id", "tax_id TEXT"),
                ("ird_password", "ird_password TEXT"),
                ("vat_registered", "vat_registered INTEGER DEFAULT 0"),
                ("vat_registered_date", "vat_registered_date TEXT"),
                ("service_type", "service_type TEXT"),
                ("num_transactions", "num_transactions TEXT"),
                ("service_fee", "service_fee TEXT"),
                ("payment_status", "payment_status TEXT"),
                ("sla", "sla TEXT"),
                ("headcount", "headcount INTEGER"),
                ("fs_status", "fs_status TEXT DEFAULT 'Not Applicable'"),
                ("pnd53_status", "pnd53_status TEXT DEFAULT 'Not Applicable'"),
                ("pp30_status", "pp30_status TEXT DEFAULT 'Not Applicable'"),
                ("pnd51_status", "pnd51_status TEXT DEFAULT 'Not Applicable'"),
                ("pnd50_status", "pnd50_status TEXT DEFAULT 'Not Applicable'"),
                ("audit_status", "audit_status TEXT DEFAULT 'Not Applicable'"),
                ("vo_address", "vo_address TEXT"),
                ("vo_service_provider", "vo_service_provider TEXT"),
                ("vo_renewal_date", "vo_renewal_date TEXT"),
                ("csh_service_provider", "csh_service_provider TEXT"),
                ("csh_renewal_date", "csh_renewal_date TEXT"),
                ("shareholder_info", "shareholder_info TEXT"),
            ):
                if name not in client_columns:
                    conn.execute(f"ALTER TABLE clients ADD COLUMN {ddl}")
        if "tasks" in existing:
            task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
            for name, ddl in (
                ("pipeline_item_id", "pipeline_item_id INTEGER"),
                ("pipeline_step", "pipeline_step INTEGER"),
                ("source_document_id", "source_document_id INTEGER"),
            ):
                if name not in task_columns:
                    conn.execute(f"ALTER TABLE tasks ADD COLUMN {ddl}")
        if "service_renewals" in existing:
            renewal_columns = {row["name"] for row in conn.execute("PRAGMA table_info(service_renewals)")}
            for name, ddl in (
                ("needs_documents", "needs_documents INTEGER NOT NULL DEFAULT 1"),
                ("task_id", "task_id INTEGER"),
            ):
                if name not in renewal_columns:
                    conn.execute(f"ALTER TABLE service_renewals ADD COLUMN {ddl}")
        if "renewal_items" in existing:
            renewal_items_columns = {row["name"] for row in conn.execute("PRAGMA table_info(renewal_items)")}
            if "template_name" not in renewal_items_columns:
                conn.execute("ALTER TABLE renewal_items RENAME TO renewal_items_old")
                conn.execute("DROP INDEX IF EXISTS sqlite_autoindex_renewal_items_1")
                conn.execute(
                    """
                    CREATE TABLE renewal_items (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id     INTEGER NOT NULL,
                        template_name TEXT    NOT NULL DEFAULT 'Visa Renewal',
                        item          TEXT    NOT NULL,
                        due_days      INTEGER NOT NULL DEFAULT 0,
                        done          INTEGER NOT NULL DEFAULT 0,
                        done_at       TEXT,
                        created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                        UNIQUE (client_id, template_name, item),
                        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                    )
                    """
                )
                # Ancient schemas may predate done_at/created_at — only
                # copy the columns that actually exist in the old table.
                old_cols = {row["name"] for row in conn.execute("PRAGMA table_info(renewal_items_old)")}
                done_at_expr = "done_at" if "done_at" in old_cols else "NULL"
                created_expr = "created_at" if "created_at" in old_cols else "datetime('now', 'localtime')"
                conn.execute(
                    f"""
                    INSERT INTO renewal_items
                        (id, client_id, template_name, item, due_days, done, done_at, created_at)
                    SELECT id, client_id, 'Visa Renewal', item, due_days, done, {done_at_expr}, {created_expr}
                    FROM renewal_items_old
                    """
                )
                conn.execute("DROP TABLE renewal_items_old")
                conn.execute("DELETE FROM sqlite_sequence WHERE name = 'renewal_items_old'")
        if "financial_documents" not in existing:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS financial_documents (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id       INTEGER,
                    category        TEXT NOT NULL,
                    subcategory     TEXT,
                    file_name       TEXT NOT NULL,
                    file_path       TEXT NOT NULL,
                    stored_path     TEXT,
                    amount          TEXT,
                    doc_date        TEXT,
                    description     TEXT,
                    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_docs_client ON financial_documents(client_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_docs_category ON financial_documents(category)")
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
            fts_row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='clients_fts'"
            ).fetchone()
            if not fts_row:
                conn.executescript(
                    """
                    CREATE VIRTUAL TABLE clients_fts USING fts5(
                        name, contact_name, email, tokenize='unicode61'
                    );
                    INSERT INTO clients_fts(rowid, name, contact_name, email)
                    SELECT id,
                           COALESCE(name, ''),
                           COALESCE(contact_name, ''),
                           COALESCE(email, '')
                    FROM clients;
                    """
                )
                CoreMixin._ensure_clients_fts_triggers(conn)
            else:
                CoreMixin._ensure_clients_fts_triggers(conn)
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()
