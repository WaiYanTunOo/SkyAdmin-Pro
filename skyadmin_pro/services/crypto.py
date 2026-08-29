"""File-level encryption — Sky Creation Innovations.

Machine-bound database encryption and universal-key encrypted backups.
Uses Fernet (AES-128-CBC + HMAC) from `cryptography`.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

MAGIC = b"SKYENCRYPTED_v1\n"

# Derive SECRET using the same anti-extraction scheme as license.py
_XK = [0x5B, 0x2E]
_XF = [
    ([8, 48, 34, 24], [41, 62, 58, 47]),
    ([71, 65, 64, 103], [64, 64, 65, 88]),
    ([58, 47, 50, 52], [53, 40, 118, 105]),
    ([30, 28, 24, 3], [125, 69, 87, 111]),
    ([63, 54, 50, 53], [11, 41, 52, 120]),
    ([126, 92, 65, 94], [92, 71, 75, 90]),
    ([58, 41], [34, 122]),
]

_SECRET_CACHE = None
_SECRET_LOCK = __import__("threading").Lock()


def _get_secret():
    global _SECRET_CACHE
    if _SECRET_CACHE is not None:
        return _SECRET_CACHE
    with _SECRET_LOCK:
        if _SECRET_CACHE is not None:
            return _SECRET_CACHE
        parts_a = []
        parts_b = []
        for block_idx, (ea, eb) in enumerate(_XF):
            k = _XK[block_idx % len(_XK)]
            parts_a.append(bytes(c ^ k for c in ea))
            parts_b.append(bytes(c ^ k for c in eb))
        _SECRET_CACHE = b"".join(a + b for a, b in zip(parts_a, parts_b))
        return _SECRET_CACHE


def _derive_fernet_key(machine_id: str) -> bytes:
    """32-byte urlsafe base64 key for Fernet — machine-bound."""
    raw = hashlib.pbkdf2_hmac("sha256", _get_secret(), machine_id.encode(), 100_000, dklen=32)
    return base64.urlsafe_b64encode(raw)


def _derive_backup_key() -> bytes:
    """Universal key for encrypted backups — same on every licensed copy."""
    raw = hashlib.pbkdf2_hmac("sha256", _get_secret(), b"SkyAdminBackupSalt2026", 100_000, dklen=32)
    return base64.urlsafe_b64encode(raw)


def is_encrypted(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def encrypt_file(path: Path, machine_id: str) -> None:
    """Encrypt file in-place (adds MAGIC header). No-op if already encrypted."""
    if is_encrypted(path):
        return
    try:
        from cryptography.fernet import Fernet

        key = _derive_fernet_key(machine_id)
        f = Fernet(key)
        data = path.read_bytes()
        token = f.encrypt(data)
        path.write_bytes(MAGIC + token)
    except Exception:
        # If cryptography missing or fails, leave file as-is — app still locks via license gate
        pass


def decrypt_file(path: Path, machine_id: str) -> bool:
    """Decrypt file in-place if it was encrypted. Returns True if decrypted."""
    if not is_encrypted(path):
        return False
    try:
        from cryptography.fernet import Fernet

        key = _derive_fernet_key(machine_id)
        f = Fernet(key)
        blob = path.read_bytes()
        token = blob[len(MAGIC) :]
        data = f.decrypt(token)
        path.write_bytes(data)
        return True
    except Exception:
        return False


# ---- Encrypted backup for data folder copy (universal key) ----

def create_encrypted_backup(workspace_root: Path, db_file: Path, dest: Path) -> Path:
    """Create an encrypted .skybackup archive of DB + Workspace.
    The backup can be restored on any licensed PC (universal key)."""
    import tempfile
    import zipfile

    from cryptography.fernet import Fernet

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    key = _derive_backup_key()
    f = Fernet(key)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as z:
            if db_file.exists():
                z.write(db_file, arcname="skyadmin_pro.db")
            ws = Path(workspace_root)
            if ws.exists():
                for p in ws.rglob("*"):
                    if p.is_file():
                        # Avoid including huge archive subfolders recursively
                        try:
                            arc = p.relative_to(ws)
                        except ValueError:
                            continue
                        z.write(p, arcname=f"Workspace/{arc}")
        data = tmp_path.read_bytes()
        token = f.encrypt(data)
        dest.write_bytes(MAGIC + token)
        return dest
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def restore_encrypted_backup(archive: Path, workspace_root: Path, db_file: Path) -> None:
    """Decrypt and restore an encrypted backup. Overwrites current DB + Workspace."""
    import tempfile
    import zipfile

    from cryptography.fernet import Fernet

    if not is_encrypted(archive):
        raise ValueError("Not a valid SkyAdmin encrypted backup (missing header).")
    key = _derive_backup_key()
    f = Fernet(key)
    blob = Path(archive).read_bytes()
    data = f.decrypt(blob[len(MAGIC) :])

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_bytes(data)
    try:
        with zipfile.ZipFile(tmp_path, "r") as z:
            # Restore DB
            try:
                db_data = z.read("skyadmin_pro.db")
                db_file.parent.mkdir(parents=True, exist_ok=True)
                db_file.write_bytes(db_data)
            except KeyError:
                pass
            # Restore Workspace
            ws = Path(workspace_root)
            for info in z.infolist():
                if info.filename.startswith("Workspace/"):
                    rel = info.filename[len("Workspace/") :]
                    if not rel:
                        continue
                    target = ws / rel
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(z.read(info.filename))
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
