"""Prefer Drive when entitled+connected; always keep a local copy."""

from __future__ import annotations

from pathlib import Path

from skyadmin_pro.services.drive.entitlement import drive_preference_on, license_allows_drive
from skyadmin_pro.services.drive.errors import NotConfiguredError
from skyadmin_pro.services.drive.tokens import load_refresh_token
from skyadmin_pro.services.storage_backend import LocalStorageBackend


def upload_document_file(
    db,
    *,
    source: Path | str,
    relpath: str,
    local_root: Path | str | None = None,
) -> dict:
    """Save document bytes; return paths and optional drive_file_id.

    Never proxies through the Worker. When Drive is entitled, enabled, and
    connected, uploads to the customer Drive and returns drive_file_id.
    Always writes a local copy under the workspace for offline use.
    """
    src = Path(source)
    data = src.read_bytes()
    if local_root is None:
        from skyadmin_pro.paths import default_workspace_root

        local_root = default_workspace_root()
    local_path = LocalStorageBackend(local_root).save_bytes(relpath, data)
    drive_file_id = ""
    if license_allows_drive(db) and drive_preference_on(db) and load_refresh_token(db):
        try:
            from skyadmin_pro.services.drive.backend import GoogleDriveStorageBackend

            drive = GoogleDriveStorageBackend(db)
            drive.save_bytes(relpath, data)
            drive_file_id = drive.last_file_id(relpath) or ""
        except NotConfiguredError:
            drive_file_id = ""
    return {
        "local_path": str(local_path),
        "drive_file_id": drive_file_id,
        "relpath": Path(relpath).as_posix(),
    }
