"""File-level encryption — Sky Creation Innovations.

Machine-bound database encryption and universal-key encrypted backups.
Uses Fernet (AES-128-CBC + HMAC) from `cryptography`.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptography.fernet import Fernet

from skyadmin_pro.paths import remove_sqlite_sidecars
from skyadmin_pro.services._secret import _derive_secret

logger = logging.getLogger(__name__)

MAGIC = b"SKYENCRYPTED_v1\n"
WORKSPACE_PREFIX = "Workspace/"


@dataclass(frozen=True)
class BackupArchiveInfo:
    has_database: bool
    database_bytes: int
    workspace_file_count: int
    workspace_bytes: int
    encrypted_bytes: int


@dataclass(frozen=True)
class RestoreSummary:
    database_bytes: int
    workspace_files_restored: int
    workspace_bytes: int


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


def encrypt_file(path: Path, machine_id: str) -> bool:
    """Encrypt *path* in place (prepends :data:`MAGIC`). Returns True on success."""
    if is_encrypted(path):
        return True
    try:
        import os
        import tempfile

        from cryptography.fernet import Fernet

        fernet = Fernet(_derive_fernet_key(machine_id, 200_000))
        data = path.read_bytes()
        encrypted = MAGIC + fernet.encrypt(data)
        path = Path(path)
        tmp_fd, tmp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".encrypting",
        )
        try:
            with os.fdopen(tmp_fd, "wb") as handle:
                handle.write(encrypted)
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        return True
    except OSError as exc:
        logger.warning("encrypt_file failed for %s: %s", path, exc)
        return False
    except Exception:
        logger.exception("encrypt_file failed for %s", path)
        return False


def decrypt_file(path: Path, machine_id: str) -> bool:
    """Decrypt *path* in place when encrypted. Returns True if decrypted."""
    if not is_encrypted(path):
        return False
    try:
        import os
        import tempfile

        from cryptography.fernet import Fernet, InvalidToken

        blob = path.read_bytes()[len(MAGIC) :]
        # Try current then legacy KDF
        for iters in (200_000, 100_000):
            try:
                fernet = Fernet(_derive_fernet_key(machine_id, iters))
                data = fernet.decrypt(blob)
                break
            except InvalidToken:
                if iters == 100_000:
                    raise
                continue
        else:
            return False
        path = Path(path)
        tmp_fd, tmp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".decrypting",
        )
        try:
            with os.fdopen(tmp_fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        return True
    except (InvalidToken, OSError, ValueError):
        logger.exception("decrypt_file failed for %s", path)
        return False


def _decrypt_backup_zip(archive: Path) -> Path:
    """Decrypt a .skybackup archive to a temporary zip file."""
    from cryptography.fernet import Fernet, InvalidToken

    archive = Path(archive)
    if not is_encrypted(archive):
        raise ValueError("Not a valid SkyAdmin encrypted backup (missing header).")

    blob = archive.read_bytes()[len(MAGIC) :]
    for iters in (200_000, 100_000):
        try:
            fernet = Fernet(_derive_backup_key(iters))
            data = fernet.decrypt(blob)
            break
        except InvalidToken:
            if iters == 100_000:
                raise ValueError("Encrypted backup could not be decrypted.") from InvalidToken()
            continue
    else:
        raise ValueError("Encrypted backup could not be decrypted.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_path = Path(tmp.name)
    tmp.write(data)
    tmp.close()
    return tmp_path


def inspect_encrypted_backup(archive: Path) -> BackupArchiveInfo:
    """Read backup metadata without restoring anything."""
    archive = Path(archive)
    tmp_path = _decrypt_backup_zip(archive)
    try:
        with zipfile.ZipFile(tmp_path, "r") as archive_zip:
            names = archive_zip.namelist()
            has_db = "skyadmin_pro.db" in names
            db_bytes = 0
            if has_db:
                db_bytes = archive_zip.getinfo("skyadmin_pro.db").file_size
            workspace_files = 0
            workspace_bytes = 0
            for info in archive_zip.infolist():
                if not info.filename.startswith(WORKSPACE_PREFIX):
                    continue
                rel = info.filename[len(WORKSPACE_PREFIX) :]
                if not rel or info.is_dir() or rel.endswith("/"):
                    continue
                workspace_files += 1
                workspace_bytes += info.file_size
        return BackupArchiveInfo(
            has_database=has_db,
            database_bytes=db_bytes,
            workspace_file_count=workspace_files,
            workspace_bytes=workspace_bytes,
            encrypted_bytes=archive.stat().st_size,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def create_encrypted_backup(workspace_root: Path, db_file: Path, dest: Path) -> Path:
    """Create an encrypted ``.skybackup`` archive of the DB and workspace tree."""
    import tempfile

    from cryptography.fernet import Fernet

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fernet = Fernet(_derive_backup_key(200_000))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as archive:
            if db_file.exists():
                archive.write(db_file, arcname="skyadmin_pro.db")
            ws = Path(workspace_root)
            if ws.exists():
                for file_path in ws.rglob("*"):
                    if not file_path.is_file():
                        continue
                    try:
                        arc = file_path.relative_to(ws)
                    except ValueError:
                        continue
                    archive.write(file_path, arcname=f"{WORKSPACE_PREFIX}{arc.as_posix()}")
        dest.write_bytes(MAGIC + fernet.encrypt(tmp_path.read_bytes()))
        return dest
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def restore_encrypted_backup(archive: Path, workspace_root: Path, db_file: Path) -> RestoreSummary:
    """Decrypt and restore an encrypted backup. Overwrites DB and workspace files."""
    archive = Path(archive)
    tmp_path = _decrypt_backup_zip(archive)
    try:
        with zipfile.ZipFile(tmp_path, "r") as archive_zip:
            names = archive_zip.namelist()
            if "skyadmin_pro.db" not in names:
                raise ValueError("Backup archive is missing skyadmin_pro.db — restore aborted.")

            ws = Path(workspace_root)
            ws.mkdir(parents=True, exist_ok=True)

            # Validate every workspace member before overwriting live data.
            workspace_entries: list[tuple[zipfile.ZipInfo, Path]] = []
            workspace_bytes = 0
            for info in archive_zip.infolist():
                if not info.filename.startswith(WORKSPACE_PREFIX):
                    continue
                rel = info.filename[len(WORKSPACE_PREFIX) :]
                if not rel:
                    continue
                target = _resolve_member_under(ws, rel)
                workspace_entries.append((info, target))
                if not info.is_dir() and not rel.endswith("/"):
                    workspace_bytes += info.file_size

            db_info = archive_zip.getinfo("skyadmin_pro.db")
            db_file = Path(db_file)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            db_file.write_bytes(archive_zip.read("skyadmin_pro.db"))
            remove_sqlite_sidecars(db_file)

            restored_files = 0
            for info, target in workspace_entries:
                rel = info.filename[len(WORKSPACE_PREFIX) :]
                if info.is_dir() or rel.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive_zip.read(info.filename))
                restored_files += 1
        return RestoreSummary(
            database_bytes=db_info.file_size,
            workspace_files_restored=restored_files,
            workspace_bytes=workspace_bytes,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
