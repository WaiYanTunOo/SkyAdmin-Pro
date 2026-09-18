from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from ._const_0 import logger
from ._const_1 import MAGIC
from ._const_2 import WORKSPACE_PREFIX
from .funcs_0 import _snapshot_db_for_backup
from .funcs_2 import _derive_backup_key


def create_encrypted_backup(workspace_root: Path, db_file: Path, dest: Path) -> Path:
    """Create an encrypted ``.skybackup`` archive of the DB and workspace tree."""

    from cryptography.fernet import Fernet

    workspace_root = Path(workspace_root)
    db_file = Path(db_file)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fernet = Fernet(_derive_backup_key(200_000))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp_path = Path(tmp.name)
    try:
        with tempfile.TemporaryDirectory(prefix="skybackup_db_") as staging:
            db_snapshot: Path | None = None
            if db_file.exists():
                from skyadmin_pro.db.cipher import DB_ERRORS as _DB_ERRORS

                try:
                    db_snapshot = _snapshot_db_for_backup(Path(db_file), Path(staging))
                except (OSError, ValueError) + _DB_ERRORS:
                    logger.warning("DB snapshot failed; falling back to raw copy", exc_info=True)
                    db_snapshot = None
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as archive:
                if db_snapshot is not None and db_snapshot.exists():
                    archive.write(db_snapshot, arcname="skyadmin_pro.db")
                elif db_file.exists():
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
                        # Don't recurse backups into themselves.
                        if arc.parts and arc.parts[0] in {"AutoBackups", "backups"}:
                            continue
                        archive.write(file_path, arcname=f"{WORKSPACE_PREFIX}{arc.as_posix()}")
        dest.write_bytes(MAGIC + fernet.encrypt(tmp_path.read_bytes()))
        return dest
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            logger.debug("Failed to unlink temp path %s", tmp_path, exc_info=True)
