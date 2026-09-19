from __future__ import annotations

import zipfile
from pathlib import Path

from skyadmin_pro.db.replace_db import replace_sqlite_db
from skyadmin_pro.paths import remove_sqlite_sidecars

from ._const_0 import logger
from ._const_2 import WORKSPACE_PREFIX
from ._types import RestoreSummary
from .funcs_0 import _verify_sqlite_bytes
from .funcs_1 import _rewrite_db_paths
from .funcs_2 import _resolve_member_under
from .funcs_4 import _decrypt_backup_zip


def restore_encrypted_backup(archive: Path, workspace_root: Path, db_file: Path) -> RestoreSummary:
    """Decrypt and restore an encrypted backup. Overwrites DB and workspace files."""
    archive = Path(archive)
    tmp_path = _decrypt_backup_zip(archive)
    paths_rewritten = 0
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
            db_payload = archive_zip.read("skyadmin_pro.db")
            # Verify on a disposable temp — never open the swap path with SQLite
            # (Windows keeps a lock on memory-mapped DB files after close).
            _verify_sqlite_bytes(db_payload)
            db_file = Path(db_file)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            staged_db = db_file.with_suffix(db_file.suffix + ".new")
            staged_db.write_bytes(db_payload)
            try:
                replace_sqlite_db(staged_db, db_file)
            except Exception:
                try:
                    staged_db.unlink(missing_ok=True)
                except OSError:
                    pass
                raise

            remove_sqlite_sidecars(db_file)

            restored_files = 0
            for info, target in workspace_entries:
                rel = info.filename[len(WORKSPACE_PREFIX) :]
                if info.is_dir() or rel.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                staged = target.with_name(target.name + ".new")
                staged.write_bytes(archive_zip.read(info.filename))
                try:
                    replace_sqlite_db(staged, target)
                except OSError:
                    target.write_bytes(staged.read_bytes())
                    staged.unlink(missing_ok=True)
                restored_files += 1

        try:
            paths_rewritten = _rewrite_db_paths(db_file, ws)
        except Exception:
            logger.warning("Path rewriting failed", exc_info=True)

        # Backups ship plaintext — encrypt after rewrite so next app open is cipher.
        try:
            from skyadmin_pro.db.cipher import migrate_plaintext_to_cipher

            migrate_plaintext_to_cipher(db_file)
        except Exception:
            logger.warning("Post-restore cipher migration failed", exc_info=True)

        return RestoreSummary(
            database_bytes=db_info.file_size,
            workspace_files_restored=restored_files,
            workspace_bytes=workspace_bytes,
            paths_rewritten=paths_rewritten,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            logger.debug("Failed to unlink temp path %s", tmp_path, exc_info=True)
