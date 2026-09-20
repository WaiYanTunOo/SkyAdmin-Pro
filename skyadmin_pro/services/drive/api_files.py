"""Drive file upload / download / delete."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from skyadmin_pro.services.drive.api_http import drive_request
from skyadmin_pro.services.drive.errors import DriveApiError

DRIVE_API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"


def upload_bytes(access: str, name: str, data: bytes, parent_id: str) -> str:
    boundary = "skyadmin_drive_boundary"
    meta = json.dumps({"name": name, "parents": [parent_id]})
    nl = "\r\n"
    preamble = (
        f"--{boundary}{nl}"
        f"Content-Type: application/json; charset=UTF-8{nl}{nl}"
        f"{meta}{nl}"
        f"--{boundary}{nl}"
        f"Content-Type: application/octet-stream{nl}{nl}"
    ).encode()
    body = preamble + data + f"{nl}--{boundary}--{nl}".encode()
    url = f"{UPLOAD_API}/files?uploadType=multipart&fields=id"
    created = drive_request(
        access,
        "POST",
        url,
        data=body,
        headers={"Content-Type": f"multipart/related; boundary={boundary}"},
    )
    return str(created["id"])


def download_bytes(access: str, file_id: str) -> bytes:
    url = f"{DRIVE_API}/files/{urllib.parse.quote(file_id)}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310 - fixed https DRIVE_API url
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise DriveApiError(f"Drive download failed: {exc.code}") from exc


def delete_file(access: str, file_id: str) -> None:
    drive_request(access, "DELETE", f"{DRIVE_API}/files/{urllib.parse.quote(file_id)}")
