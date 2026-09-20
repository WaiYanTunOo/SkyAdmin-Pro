from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from ._const_0 import logger
from ._const_1 import CIPHER_KDF_ITERATIONS
from ._const_2 import CIPHER_PBKDF2_ITERATIONS
from ._const_3 import SQLITE_MAGIC


def driver() -> Any:
    """Return the SQLCipher DB-API module, or raise with install hint."""
    from skyadmin_pro.db import cipher as cipher_mod

    if not cipher_mod.HAS_CIPHER:
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
        env_id = os.environ.get("SKYADMIN_MACHINE_ID", "").strip()
        if env_id:
            logger.info("Using SKYADMIN_MACHINE_ID env var for database key")
            return env_id.encode("utf-8")
        raise RuntimeError(
            "Machine ID unavailable — cannot derive database key. "
            "Reinstall the application or set the SKYADMIN_MACHINE_ID environment variable."
        ) from None


def derive_db_key_hex() -> str:
    """Machine-bound 256-bit key, hex-encoded for ``PRAGMA key = "x'..'"``."""
    from skyadmin_pro.services._secret import _derive_secret

    raw = hashlib.pbkdf2_hmac("sha256", _derive_secret(), _machine_salt(), CIPHER_PBKDF2_ITERATIONS, dklen=32)
    return raw.hex()


def connect(
    db_file: str | Path, *, timeout: int = 10, key_hex: str | None = None, check_same_thread: bool = True
) -> Any:
    """Open a keyed SQLCipher connection (fails closed without the driver).

    ``check_same_thread`` forwards to the driver so the pool owner (main
    thread) can close background handles deterministically in shutdown().
    """
    drv = driver()
    key = key_hex or derive_db_key_hex()
    if not all(c in "0123456789abcdef" for c in key):
        raise ValueError("Invalid database key format — expected hex string")
    conn = drv.connect(str(db_file), timeout=timeout, check_same_thread=check_same_thread)
    try:
        conn.execute(f"PRAGMA kdf_iter = {int(CIPHER_KDF_ITERATIONS)}")
        conn.execute(f"PRAGMA key = \"x'{key}'\"")
    except Exception:
        conn.close()
        raise
    return conn


def db_state(path: str | Path) -> str:
    """Classify 'new', 'plaintext', or 'cipher'; when unsure, callers should keyed-open."""
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
