"""Minimal Google Drive REST helpers (urllib)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from skyadmin_pro.services.drive.api_files import delete_file, download_bytes, upload_bytes
from skyadmin_pro.services.drive.api_http import drive_request
from skyadmin_pro.services.drive.errors import DriveApiError, NotConfiguredError
from skyadmin_pro.services.drive.tokens import (
    load_refresh_token,
    resolve_client_id,
    resolve_client_secret,
)

TOKEN_URI = "https://oauth2.googleapis.com/token"
DRIVE_API = "https://www.googleapis.com/drive/v3"

__all__ = [
    "DRIVE_API",
    "delete_file",
    "download_bytes",
    "drive_request",
    "ensure_folder",
    "refresh_access_token",
    "upload_bytes",
]


def refresh_access_token(db) -> str:
    refresh = load_refresh_token(db)
    client_id = resolve_client_id(db)
    client_secret = resolve_client_secret(db)
    if not refresh or not client_id or not client_secret:
        raise NotConfiguredError("Google Drive is not connected.")
    data = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(TOKEN_URI, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise DriveApiError(f"Token refresh failed: {exc.code}") from exc
    token = (payload.get("access_token") or "").strip()
    if not token:
        raise DriveApiError("Token refresh returned no access_token.")
    return token


def ensure_folder(access: str, name: str, parent_id: str | None = None) -> str:
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    url = f"{DRIVE_API}/files?q={urllib.parse.quote(q)}&spaces=drive&fields=files(id,name)"
    found = drive_request(access, "GET", url)
    files = found.get("files") or []
    if files:
        return str(files[0]["id"])
    meta: dict = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    created = drive_request(
        access,
        "POST",
        f"{DRIVE_API}/files?fields=id",
        data=json.dumps(meta).encode(),
        headers={"Content-Type": "application/json"},
    )
    return str(created["id"])
