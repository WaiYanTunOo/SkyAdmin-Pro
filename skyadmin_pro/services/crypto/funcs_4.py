from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from ._const_0 import logger
from ._const_1 import MAGIC
from ._const_2 import WORKSPACE_PREFIX
from ._types import BackupArchiveInfo
from .funcs_2 import _derive_backup_key, is_encrypted


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

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
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
            logger.debug("Failed to unlink temp path %s", tmp_path, exc_info=True)
