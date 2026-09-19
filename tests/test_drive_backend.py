"""Google Drive storage backend + entitlement gate (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from skyadmin_pro.services.drive.backend import GoogleDriveStorageBackend
from skyadmin_pro.services.drive.entitlement import (
    drive_connect_unlocked,
    license_allows_drive,
    set_license_entitlements,
)
from skyadmin_pro.services.drive.errors import NotConfiguredError
from skyadmin_pro.services.drive.keys import SETTING_DRIVE_FILES_ENABLED
from skyadmin_pro.services.drive.upload import upload_document_file


class _MemDb:
    def __init__(self):
        self._s: dict[str, str] = {}

    def get_setting(self, key, default=""):
        return self._s.get(key, default)

    def set_setting(self, key, value):
        self._s[key] = str(value)


def test_drive_connect_locked_without_license():
    db = _MemDb()
    assert license_allows_drive(db) is False
    assert drive_connect_unlocked(db) is False
    set_license_entitlements(db, drive_files=1)
    assert license_allows_drive(db) is True
    assert drive_connect_unlocked(db) is True


def test_drive_backend_raises_without_token():
    db = _MemDb()
    backend = GoogleDriveStorageBackend(db)
    with pytest.raises(NotConfiguredError):
        backend.save_bytes("a.pdf", b"x")


def test_drive_save_bytes_roundtrip_mocked():
    db = _MemDb()
    backend = GoogleDriveStorageBackend(db)
    with (
        patch("skyadmin_pro.services.drive.backend.load_refresh_token", return_value="refresh"),
        patch("skyadmin_pro.services.drive.api.refresh_access_token", return_value="access"),
        patch(
            "skyadmin_pro.services.drive.api.ensure_folder",
            side_effect=lambda *a, **k: f"id-{a[1]}",
        ),
        patch("skyadmin_pro.services.drive.api.upload_bytes", return_value="file123") as up,
        patch("skyadmin_pro.services.drive.api.download_bytes", return_value=b"hello"),
    ):
        path = backend.save_bytes("Clients/Acme/note.txt", b"hello")
        assert "file123" in str(path)
        up.assert_called_once()
        assert backend.read_bytes("Clients/Acme/note.txt") == b"hello"
        assert backend.exists("Clients/Acme/note.txt")


def test_upload_document_file_local_and_drive(tmp_path):
    db = _MemDb()
    set_license_entitlements(db, drive_files=1)
    db.set_setting(SETTING_DRIVE_FILES_ENABLED, "1")
    src = tmp_path / "in.pdf"
    src.write_bytes(b"%PDF-1.4")
    inst = MagicMock()
    inst.save_bytes.return_value = tmp_path / "d"
    inst.last_file_id.return_value = "gid-9"
    with (
        patch("skyadmin_pro.services.drive.upload.load_refresh_token", return_value="refresh"),
        patch(
            "skyadmin_pro.services.drive.upload.GoogleDriveStorageBackend",
            create=True,
        ),
        patch(
            "skyadmin_pro.services.drive.backend.GoogleDriveStorageBackend",
            return_value=inst,
        ),
    ):
        result = upload_document_file(db, source=src, relpath="Files/in.pdf", local_root=tmp_path)
    assert (tmp_path / "Files" / "in.pdf").read_bytes() == b"%PDF-1.4"
    assert result["drive_file_id"] == "gid-9"
    assert result["local_path"]
