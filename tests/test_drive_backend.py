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


def test_drive_oauth_client_config_roundtrip():
    from skyadmin_pro.services.drive import tokens
    from skyadmin_pro.services.drive.tokens import (
        resolve_client_id,
        resolve_client_secret,
        save_client_config,
    )

    db = _MemDb()
    with patch.object(tokens, "BUNDLED_GOOGLE_OAUTH_CLIENT_ID", ""):
        assert resolve_client_id(db) == ""
        assert resolve_client_secret(db) == ""
        save_client_config(db, "cid-1", "csecret-1")
        assert resolve_client_id(db) == "cid-1"
        assert resolve_client_secret(db) == "csecret-1"


def test_resolve_client_id_falls_back_to_bundled():
    from skyadmin_pro.services.drive import tokens

    db = _MemDb()
    with patch.object(tokens, "BUNDLED_GOOGLE_OAUTH_CLIENT_ID", "bundled-cid"):
        assert tokens.resolve_client_id(db) == "bundled-cid"


def test_connect_google_drive_requires_oauth_client():
    from skyadmin_pro.services.drive import tokens
    from skyadmin_pro.services.drive.oauth import connect_google_drive

    db = _MemDb()
    with (
        patch.object(tokens, "BUNDLED_GOOGLE_OAUTH_CLIENT_ID", ""),
        pytest.raises(NotConfiguredError, match="Google OAuth is not configured"),
    ):
        connect_google_drive(db, timeout_sec=0.1)


def test_pkce_exchange_omits_secret_when_empty():
    from skyadmin_pro.services.drive import oauth_pkce

    captured: dict = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"refresh_token":"rt","access_token":"at"}'

    def fake_urlopen(req, timeout=30):
        captured["body"] = req.data.decode()
        return _Resp()

    with patch("skyadmin_pro.services.drive.oauth_pkce.urllib.request.urlopen", side_effect=fake_urlopen):
        out = oauth_pkce.exchange_code("cid", "", "code", "http://127.0.0.1:9/", "verifier")
    assert out["refresh_token"] == "rt"
    assert "code_verifier=verifier" in captured["body"]
    assert "client_secret" not in captured["body"]


def test_pkce_exchange_surfaces_google_error():
    import io
    import urllib.error as ue

    from skyadmin_pro.services.drive import oauth_pkce

    err = ue.HTTPError(
        "https://oauth2.googleapis.com/token",
        401,
        "Unauthorized",
        hdrs=None,
        fp=io.BytesIO(b'{"error":"invalid_client","error_description":"Unauthorized"}'),
    )
    with (
        patch("skyadmin_pro.services.drive.oauth_pkce.urllib.request.urlopen", side_effect=err),
        pytest.raises(NotConfiguredError, match="Client secret"),
    ):
        oauth_pkce.exchange_code("cid", "", "code", "http://127.0.0.1:9/", "verifier")


def test_pkce_exchange_redacts_client_secret_in_errors():
    import io
    import urllib.error as ue

    from skyadmin_pro.services.drive import oauth_pkce

    secret = "super-secret-value-xyz"
    err = ue.HTTPError(
        "https://oauth2.googleapis.com/token",
        400,
        "Bad Request",
        hdrs=None,
        fp=io.BytesIO(f'{{"error":"invalid_client","error_description":"bad {secret}"}}'.encode()),
    )
    with (
        patch("skyadmin_pro.services.drive.oauth_pkce.urllib.request.urlopen", side_effect=err),
        pytest.raises(NotConfiguredError) as raised,
    ):
        oauth_pkce.exchange_code("cid", secret, "code", "http://127.0.0.1:9/", "verifier")
    assert secret not in str(raised.value)
    assert "[redacted]" in str(raised.value)


def test_refresh_access_token_without_secret():
    from skyadmin_pro.services.drive import api
    from skyadmin_pro.services.drive.keys import SETTING_DRIVE_REFRESH_TOKEN
    from skyadmin_pro.services.secret_fields import encrypt_secret

    db = _MemDb()
    db.set_setting(SETTING_DRIVE_REFRESH_TOKEN, encrypt_secret("refresh-tok"))
    captured: dict = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"access_token":"access-1"}'

    def fake_urlopen(req, timeout=30):
        captured["body"] = req.data.decode()
        return _Resp()

    with (
        patch.object(api, "resolve_client_id", return_value="cid"),
        patch.object(api, "resolve_client_secret", return_value=""),
        patch("skyadmin_pro.services.drive.api.urllib.request.urlopen", side_effect=fake_urlopen),
    ):
        assert api.refresh_access_token(db) == "access-1"
    assert "client_secret" not in captured["body"]
    assert "refresh_token=refresh-tok" in captured["body"]


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
