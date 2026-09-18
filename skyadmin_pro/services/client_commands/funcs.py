from __future__ import annotations

from skyadmin_pro.db.cipher import DB_ERRORS

from ..importer.funcs import Database


def _linked_tables(db: Database) -> list[str]:
    """All tables carrying a client_id column (delete-undo snapshot scope)."""
    tables = [
        row["name"]
        for row in db._fetch_all("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
    ]
    linked = []
    with db.connection() as conn:
        for table in tables:
            try:
                cols = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
            except DB_ERRORS:
                continue
            if "client_id" in cols:
                linked.append(table)
    return linked
