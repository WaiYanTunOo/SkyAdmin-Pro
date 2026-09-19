"""Shared Drive HTTP request helper."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from skyadmin_pro.services.drive.errors import DriveApiError


def drive_request(access: str, method: str, url: str, *, data: bytes | None = None, headers: dict | None = None) -> Any:
    hdrs = {"Authorization": f"Bearer {access}", **(headers or {})}
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            if not body:
                return {}
            return json.loads(body.decode())
    except urllib.error.HTTPError as exc:
        raise DriveApiError(f"Drive API {method} failed: {exc.code}") from exc
