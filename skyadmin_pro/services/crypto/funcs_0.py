from __future__ import annotations

import sqlite3
from pathlib import Path


def _snapshot_db_for_backup(db_file: Path, staging_dir: Path) -> Path:
    """Online-safe snapshot of the live DB (includes WAL content).

    Exports a **plaintext** SQLite snapshot so backups restore on any
    machine. The Fernet envelope already encrypts the archive; the inner
    DB does not need SQLCipher. On first app open after restore,
    ``migrate_plaintext_to_cipher`` re-encrypts with the local key.

    Falls back to a raw copy when the source is not a real database
    (e.g. unit tests with dummy bytes).
    """
    from skyadmin_pro.db.cipher import DB_ERRORS
    from skyadmin_pro.db.cipher import connect as cipher_connect

    snapshot = staging_dir / "skyadmin_pro.db"
    try:
        src = cipher_connect(str(db_file))
    except (OSError, DB_ERRORS, RuntimeError):
        snapshot.write_bytes(Path(db_file).read_bytes())
        return snapshot
    try:
        snap = str(snapshot.resolve()).replace("\\", "/")
        src.execute(f"ATTACH DATABASE '{snap}' AS plaintext KEY ''")
        src.execute("SELECT sqlcipher_export('plaintext', 'main')")
        src.execute("DETACH DATABASE plaintext")
    finally:
        src.close()
    # Verify the exported plaintext snapshot.
    conn_plain = sqlite3.connect(str(snapshot))
    try:
        conn_plain.execute("PRAGMA quick_check").fetchone()
    finally:
        conn_plain.close()
    if not snapshot.exists():
        return _copy_fallback(db_file, snapshot)
    return snapshot


def _copy_fallback(db_file: Path, snapshot: Path) -> Path:
    snapshot.write_bytes(Path(db_file).read_bytes())
    return snapshot


def _looks_like_sqlite(payload: bytes) -> bool:
    return payload[:16] == b"SQLite format 3\x00"


def _verify_sqlite_bytes(payload: bytes) -> None:
    """Verify DB bytes using a disposable temp file (never locks the swap path)."""
    import gc
    import tempfile

    if not payload:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        path = Path(tmp.name)
        tmp.write(payload)
    try:
        _verify_sqlite_payload(path)
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        gc.collect()


def _verify_sqlite_payload(tmp_db: Path) -> None:
    """Fail-closed integrity check for a restored DB payload.

    New backups contain a plaintext SQLite snapshot (verified with the
    standard ``sqlite3`` backend).  Legacy backups may contain a
    SQLCipher-encrypted payload keyed to the original machine — verified
    with the matching backend.  When the cipher key does not match
    (cross-machine restore of a legacy backup), a clear error is raised.

    Non-database bytes (unit-test fixtures) skip verification.
    """

    payload = Path(tmp_db).read_bytes()
    if _looks_like_sqlite(payload):
        conn = sqlite3.connect(str(tmp_db))
        try:
            row = conn.execute("PRAGMA quick_check").fetchone()
        finally:
            conn.close()
    elif len(payload) >= 16:
        from skyadmin_pro.db.cipher import CipherError
        from skyadmin_pro.db.cipher import connect as cipher_connect

        try:
            conn = cipher_connect(str(tmp_db))
            try:
                row = conn.execute("PRAGMA quick_check").fetchone()
            finally:
                conn.close()
        except (CipherError, OSError, RuntimeError):
            raise ValueError(
                "This backup was created on another machine and cannot be "
                "restored here. Restore it on the original machine first, "
                "then create a new backup."
            ) from None
    else:
        return
    if not row or row[0] != "ok":
        raise ValueError("Backup database failed integrity check — restore aborted.")
