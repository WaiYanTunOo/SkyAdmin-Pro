"""GoogleDriveStorageBackend — customer Drive, never through Worker."""

from __future__ import annotations

from pathlib import Path

from skyadmin_pro.services.drive import api as drive_api
from skyadmin_pro.services.drive.errors import DriveApiError, NotConfiguredError
from skyadmin_pro.services.drive.tokens import load_id_map, load_refresh_token, save_id_map


class GoogleDriveStorageBackend:
    """Plane B file store keyed by relative path under SkyAdmin/Files."""

    def __init__(self, db) -> None:
        self._db = db
        self._id_map: dict[str, str] = load_id_map(db)

    def _access(self) -> str:
        if not load_refresh_token(self._db):
            raise NotConfiguredError("Google Drive is not connected.")
        try:
            return drive_api.refresh_access_token(self._db)
        except DriveApiError:
            raise NotConfiguredError("Drive session expired — reconnect.") from None

    def _ensure_path_folder(self, access: str, relpath: str) -> tuple[str, str]:
        parts = Path(relpath).as_posix().strip("/").split("/")
        if not parts or parts == [""]:
            raise ValueError("relpath required")
        name = parts[-1]
        folder_id = drive_api.ensure_folder(access, "SkyAdmin")
        folder_id = drive_api.ensure_folder(access, "Files", folder_id)
        for part in parts[:-1]:
            folder_id = drive_api.ensure_folder(access, part, folder_id)
        return folder_id, name

    def save_bytes(self, relpath: str, data: bytes) -> Path:
        access = self._access()
        parent_id, name = self._ensure_path_folder(access, relpath)
        file_id = drive_api.upload_bytes(access, name, data, parent_id)
        self._id_map[Path(relpath).as_posix()] = file_id
        save_id_map(self._db, self._id_map)
        # Path-like sentinel so Protocol callers keep working; id is queryable.
        return Path(f"drive://{file_id}")

    def last_file_id(self, relpath: str) -> str | None:
        return self._id_map.get(Path(relpath).as_posix())

    def read_bytes(self, relpath: str) -> bytes:
        access = self._access()
        file_id = self._id_map.get(Path(relpath).as_posix())
        if not file_id:
            raise FileNotFoundError(relpath)
        return drive_api.download_bytes(access, file_id)

    def delete(self, relpath: str) -> bool:
        access = self._access()
        key = Path(relpath).as_posix()
        file_id = self._id_map.pop(key, None)
        if not file_id:
            return False
        drive_api.delete_file(access, file_id)
        save_id_map(self._db, self._id_map)
        return True

    def exists(self, relpath: str) -> bool:
        return Path(relpath).as_posix() in self._id_map

    def list_rel(self, prefix: str = "") -> list[str]:
        pre = Path(prefix).as_posix().strip("/") if prefix else ""
        keys = sorted(self._id_map)
        if not pre:
            return keys
        return [k for k in keys if k == pre or k.startswith(pre + "/")]
