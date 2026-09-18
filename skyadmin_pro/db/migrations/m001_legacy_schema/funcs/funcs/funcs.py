from __future__ import annotations

from skyadmin_pro.db.cipher import CipherError, CipherRow
from skyadmin_pro.db.cipher import connect as cipher_connect

from ._upgrade_columns import _upgrade_columns
from ._upgrade_sync import _upgrade_sync
from ._upgrade_tables import _upgrade_tables


def upgrade(db: CoreMixin) -> None:
    # Local import: core imports this package inside _initialize, so a
    # top-level import would be circular. Only needed for FTS triggers.

    conn = cipher_connect(str(db.db_file), timeout=10)
    conn.row_factory = CipherRow
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.isolation_level = None  # manual transaction control
        conn.execute("BEGIN IMMEDIATE")
        existing = _upgrade_columns(conn)
        _upgrade_tables(conn, existing)
        _upgrade_sync(conn, existing)
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except CipherError:
            pass
        raise
    finally:
        conn.close()
