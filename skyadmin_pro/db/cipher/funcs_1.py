from __future__ import annotations

import sqlite3
from pathlib import Path

from ._const_0 import logger
from .funcs_0 import connect, db_state, derive_db_key_hex


def migrate_plaintext_to_cipher(path: str | Path, *, key_hex: str | None = None) -> bool:
    """One-time upgrade of a plaintext DB to SQLCipher (atomic swap).

    Returns True when a migration ran, False when the file was already
    cipher/new (nothing to do). Raises on failure with the original file
    untouched.
    """
    from skyadmin_pro.db.replace_db import replace_sqlite_db
    from skyadmin_pro.paths import remove_sqlite_sidecars

    p = Path(path)
    if db_state(p) != "plaintext":
        return False
    key = key_hex or derive_db_key_hex()
    tmp = p.with_suffix(p.suffix + ".cipher_new")
    if tmp.exists():
        tmp.unlink()
    cipher_conn = connect(tmp, key_hex=key)
    try:
        # Forward slashes avoid Windows path escaping issues in SQL.
        plain = str(p.resolve()).replace("\\", "/")
        cipher_conn.execute(f"ATTACH DATABASE '{plain}' AS plaintext KEY ''")
        try:
            cipher_conn.execute("SELECT sqlcipher_export('main', 'plaintext')")
        finally:
            cipher_conn.execute("DETACH DATABASE plaintext")
        cipher_conn.commit()
        row = cipher_conn.execute("PRAGMA quick_check").fetchone()
        if not row or row[0] != "ok":
            raise ValueError("migrated database failed integrity check")
        plain_tables = _table_names(p, plaintext=True)
        cipher_tables = {
            r[0] for r in cipher_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if not set(plain_tables) <= cipher_tables:
            raise ValueError("migrated database is missing tables")
    finally:
        cipher_conn.close()
    try:
        replace_sqlite_db(tmp, p)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
    remove_sqlite_sidecars(p)
    logger.info("Migrated plaintext database to SQLCipher: %s", p)
    return True


def _table_names(path: Path, *, plaintext: bool = False) -> set[str]:
    conn = sqlite3.connect(str(path)) if plaintext else connect(path)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    finally:
        conn.close()
