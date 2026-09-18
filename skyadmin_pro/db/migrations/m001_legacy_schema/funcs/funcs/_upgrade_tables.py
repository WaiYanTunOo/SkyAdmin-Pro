from __future__ import annotations


def _upgrade_tables(conn, existing) -> None:
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
