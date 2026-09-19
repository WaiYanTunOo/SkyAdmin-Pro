from __future__ import annotations

from pathlib import Path

from ._const_0 import logger


def _rewrite_db_paths(db_file: Path, new_workspace: Path) -> int:
    """Rewrite stale absolute paths in the restored DB to *new_workspace*.

    Scans ``documents.file_path``, ``financial_documents.file_path``,
    ``financial_documents.stored_path``, and ``settings.workspace_root``.
    Returns the number of rows updated.
    """
    from skyadmin_pro.config import SETTING_WORKSPACE_ROOT

    new_root = str(new_workspace.resolve())

    # Open by header type — never probe plaintext with SQLCipher (HMAC noise + fail).
    from skyadmin_pro.db.cipher import db_state

    conn = None
    try:
        state = db_state(db_file)
        if state == "plaintext":
            import sqlite3 as _sqlite3

            conn = _sqlite3.connect(str(db_file))
        else:
            from skyadmin_pro.db.cipher import connect as cipher_connect

            conn = cipher_connect(str(db_file))
            conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
    except Exception:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.debug("Failed to close DB connection", exc_info=True)
            conn = None
        try:
            import sqlite3 as _sqlite3

            conn = _sqlite3.connect(str(db_file))
        except Exception:
            logger.warning("Cannot open restored DB for path rewriting", exc_info=True)
            return 0

    updated = 0
    try:
        # Detect the old workspace root stored in settings.
        try:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (SETTING_WORKSPACE_ROOT,),
            ).fetchone()
        except Exception:
            row = None

        old_root = row[0] if row and row[0] else None
        if not old_root or old_root == new_root:
            return 0

        old_prefix = old_root + "%"
        # Rewrite document file paths using prefix replacement.
        for table, column in (
            ("documents", "file_path"),
            ("financial_documents", "file_path"),
            ("financial_documents", "stored_path"),
        ):
            try:
                # Count matching rows before the update.
                cnt = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {column} LIKE ?",
                    (old_prefix,),
                ).fetchone()[0]
                if cnt:
                    conn.execute(
                        f"UPDATE {table} SET {column} = ? || SUBSTR({column}, ?)",
                        (new_root, len(old_root) + 1),
                    )
                    updated += cnt
            except Exception:
                logger.debug("Table %s not found during path rewrite", table)

        # Update the workspace_root setting.
        try:
            conn.execute(
                "UPDATE settings SET value = ? WHERE key = ?",
                (new_root, SETTING_WORKSPACE_ROOT),
            )
        except Exception:
            logger.debug("Settings table not found during path rewrite")

        conn.commit()
        if updated:
            logger.info(
                "Rewrote %d path(s) from %s -> %s",
                updated,
                old_root,
                new_root,
            )
    finally:
        try:
            conn.close()
        except Exception:
            logger.debug("Failed to close connection after path rewrite", exc_info=True)
    return updated
