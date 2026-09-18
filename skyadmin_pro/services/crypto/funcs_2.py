from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from skyadmin_pro.services._secret import _derive_secret

from ._const_1 import MAGIC


def format_byte_size(num_bytes: int) -> str:
    size = float(max(num_bytes, 0))
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _derive_fernet_key(machine_id: str, iterations: int = 200_000) -> bytes:
    """Return a 32-byte urlsafe base64 Fernet key bound to *machine_id*."""
    raw = hashlib.pbkdf2_hmac("sha256", _derive_secret(), machine_id.encode(), iterations, dklen=32)
    return base64.urlsafe_b64encode(raw)


def _derive_backup_key(iterations: int = 200_000) -> bytes:
    """Return the universal Fernet key used for encrypted ``.skybackup`` archives."""
    raw = hashlib.pbkdf2_hmac("sha256", _derive_secret(), b"SkyAdminBackupSalt2026", iterations, dklen=32)
    return base64.urlsafe_b64encode(raw)


def _fernet_for_machine(machine_id: str, try_legacy: bool = True) -> Fernet:
    """Get Fernet for machine, trying current then legacy iteration count."""
    from cryptography.fernet import Fernet

    # Current 200k
    try:
        return Fernet(_derive_fernet_key(machine_id, 200_000))
    except ValueError:
        if try_legacy:
            return Fernet(_derive_fernet_key(machine_id, 100_000))
        raise


def _resolve_member_under(base: Path, relative_name: str) -> Path:
    """Resolve a zip member path safely under *base* (rejects Zip Slip).

    Args:
        base: Root directory that extracted files must stay inside.
        relative_name: Archive member path relative to *base* (no leading slash).

    Returns:
        Absolute resolved path under *base*.

    Raises:
        ValueError: If the member path escapes *base* or is absolute.
    """
    clean = (relative_name or "").replace("\\", "/").lstrip("/")
    if not clean or clean.endswith("/"):
        raise ValueError(f"Invalid archive member path: {relative_name!r}")
    if Path(clean).is_absolute():
        raise ValueError(f"Absolute archive paths are not allowed: {relative_name!r}")

    root = base.resolve()
    target = (root / clean).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Archive member escapes destination directory: {relative_name!r}")
    return target


def is_encrypted(path: Path) -> bool:
    """Return True when *path* begins with the SkyAdmin encrypted-file header."""
    try:
        with open(path, "rb") as handle:
            return handle.read(len(MAGIC)) == MAGIC
    except OSError:
        return False
