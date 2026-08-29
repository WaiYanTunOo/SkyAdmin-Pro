"""File-level encryption — Sky Creation Innovations.

Machine-bound database encryption and universal-key encrypted backups.
Uses Fernet (AES-128-CBC + HMAC) from `cryptography`.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from skyadmin_pro.services._secret import _derive_secret

MAGIC = b"SKYENCRYPTED_v1\n"


def _derive_fernet_key(machine_id: str) -> bytes:
    """32-byte urlsafe base64 key for Fernet — machine-bound."""
    raw = hashlib.pbkdf2_hmac("sha256", _derive_secret(), machine_id.encode(), 100_000, dklen=32)
    return base64.urlsafe_b64encode(raw)


def _derive_backup_key() -> bytes:
    """Universal key for encrypted backups — same on every licensed copy."""
    raw = hashlib.pbkdf2_hmac("sha256", _derive_secret(), b"SkyAdminBackupSalt2026", 100_000, dklen=32)
    return base64.urlsafe_b64encode(raw)


def is_encrypted(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def encrypt_file(path: Path, machine_id: str) -> bool:
    """Encrypt file in-place (adds MAGIC header). Returns True when encrypted."""
    if is_encrypted(path):
        return True
    try:
        from cryptography.fernet import Fernet

        key = _derive_fernet_key(machine_id)
        f = Fernet(key)
        data = path.read_bytes()
        token = f.encrypt(data)
        path.write_bytes(MAGIC + token)
        return True
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("encrypt_file failed for %s: %s", path, exc, exc_info=True)
        return False


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
            if "skyadmin_pro.db" not in z.namelist():
                raise ValueError("Backup archive is missing skyadmin_pro.db — restore aborted.")
            db_data = z.read("skyadmin_pro.db")
            db_file.parent.mkdir(parents=True, exist_ok=True)
            db_file.write_bytes(db_data)
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
