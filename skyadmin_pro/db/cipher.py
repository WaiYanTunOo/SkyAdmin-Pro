"""SQLCipher live-database encryption (Phase 1).

The live ``skyadmin_pro.db`` is encrypted with SQLCipher (AES-256-CBC +
HMAC), keyed by a machine-bound PBKDF2 derivation. This module owns the
driver import, key derivation, plaintext detection, and the one-time
plaintext-to-cipher migration.

Conventions:
* Key format on the wire: ``PRAGMA key = "x'<64 hex chars>'"``.
* KDF iterations for connection open are lowered from the SQLCipher
  default (256k) to 64k: the key itself is 256-bit machine-bound entropy,
  so iteration count is defense-in-depth, and every pooled checkout pays
  the derivation cost.
* Tests set ``SKYADMIN_CIPHER_SALT`` (see ``tests/conftest.py``) so the
  suite never touches the real ``hardware.id``.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CIPHER_KDF_ITERATIONS = 64_000
CIPHER_PBKDF2_ITERATIONS = 200_000
SQLITE_MAGIC = b"SQLite format 3\x00"

try:  # Fail-closed at connect time if the driver is missing (see driver()).
    from sqlcipher3.dbapi2 import Connection as CipherConnection
    from sqlcipher3.dbapi2 import DatabaseError as CipherDatabaseError
    from sqlcipher3.dbapi2 import Error as CipherError
    from sqlcipher3.dbapi2 import IntegrityError as CipherIntegrityError
    from sqlcipher3.dbapi2 import OperationalError as CipherOperationalError
    from sqlcipher3.dbapi2 import ProgrammingError as CipherProgrammingError
    from sqlcipher3.dbapi2 import Row as CipherRow

    HAS_CIPHER = True
except ImportError:  # pragma: no cover — production always has the driver.
    CipherConnection = Any  # type: ignore[assignment,misc]
    CipherDatabaseError = Exception  # type: ignore[assignment,misc]
    CipherError = Exception  # type: ignore[assignment,misc]
    CipherIntegrityError = Exception  # type: ignore[assignment,misc]
    CipherOperationalError = Exception  # type: ignore[assignment,misc]
    CipherProgrammingError = Exception  # type: ignore[assignment,misc]
    CipherRow = Any  # type: ignore[assignment,misc]
    HAS_CIPHER = False

#: Any live-DB handle in the app (cipher in production).
DBConnection = Any

#: Catch-alls for code that must work regardless of backend.
DB_ERRORS: tuple[type[BaseException], ...] = (sqlite3.Error, CipherError)
INTEGRITY_ERRORS: tuple[type[BaseException], ...] = (
    sqlite3.IntegrityError,
    CipherIntegrityError,
)
OPERATIONAL_ERRORS: tuple[type[BaseException], ...] = (
    sqlite3.OperationalError,
    CipherOperationalError,
)


def driver() -> Any:
    """Return the SQLCipher DB-API module, or raise with install hint."""
    if not HAS_CIPHER:
        raise RuntimeError(
            "sqlcipher3 is required for the encrypted live database. Install with: pip install sqlcipher3>=0.6.2"
        )
    from sqlcipher3 import dbapi2 as drv

    return drv


def _machine_salt() -> bytes:
    override = os.environ.get("SKYADMIN_CIPHER_SALT", "").strip()
    if override:
        return override.encode("utf-8")
    try:
        from skyadmin_pro.services.license.machine import get_machine_id

        return get_machine_id().encode("utf-8")
    except Exception:
        logger.warning("Machine ID unavailable; database key uses app salt only (relocatable, weaker binding)")
        return b"SkyAdminDBSalt-v1"


def derive_db_key_hex() -> str:
    """Machine-bound 256-bit key, hex-encoded for ``PRAGMA key = "x'..'"``."""
    from skyadmin_pro.services._secret import _derive_secret

    raw = hashlib.pbkdf2_hmac("sha256", _derive_secret(), _machine_salt(), CIPHER_PBKDF2_ITERATIONS, dklen=32)
    return raw.hex()


def connect(db_file: str | Path, *, timeout: int = 10, key_hex: str | None = None) -> Any:
    """Open a keyed SQLCipher connection (fails closed without the driver)."""
    drv = driver()
    key = key_hex or derive_db_key_hex()
    assert all(c in "0123456789abcdef" for c in key), "key must be hex"
    conn = drv.connect(str(db_file), timeout=timeout)
    try:
        conn.execute(f"PRAGMA kdf_iter = {int(CIPHER_KDF_ITERATIONS)}")
        conn.execute(f"PRAGMA key = \"x'{key}'\"")
    except Exception:
        conn.close()
        raise
    return conn


def db_state(path: str | Path) -> str:
    """Classify a database file: 'new', 'plaintext', or 'cipher'.

    'cipher' means non-magic header (encrypted) — or any file we cannot
    read; callers needing certainty should attempt a keyed open.
    """
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return "new"
    try:
        with open(p, "rb") as fh:
            header = fh.read(16)
    except OSError:
        return "cipher"
    if header == SQLITE_MAGIC:
        return "plaintext"
    return "cipher"


def verify_cipher_db(path: str | Path, *, key_hex: str | None = None) -> bool:
    """Return True when *path* opens with the key and passes quick_check."""
    conn = connect(path, key_hex=key_hex)
    try:
        row = conn.execute("PRAGMA quick_check").fetchone()
        return bool(row) and row[0] == "ok"
    finally:
        conn.close()


def migrate_plaintext_to_cipher(path: str | Path, *, key_hex: str | None = None) -> bool:
    """One-time upgrade of a plaintext DB to SQLCipher (atomic swap).

    Returns True when a migration ran, False when the file was already
    cipher/new (nothing to do). Raises on failure with the original file
    untouched.
    """
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
        cipher_conn.execute(f"ATTACH DATABASE '{p}' AS plaintext KEY ''")
        try:
            cipher_conn.execute("SELECT sqlcipher_export('main', 'plaintext')")
        finally:
            cipher_conn.execute("DETACH DATABASE plaintext")
        cipher_conn.commit()
        # Verify the migrated copy before it touches the live path.
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
        os.replace(tmp, p)
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
