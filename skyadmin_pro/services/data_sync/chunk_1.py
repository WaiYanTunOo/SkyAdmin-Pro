from __future__ import annotations

from ._common import *
from ._common import get_machine_id, live_api_base_url
from .chunk_0 import _license_code, load_sync_credentials, save_sync_credentials


def register_sync_device(timeout: float = 10.0) -> tuple[bool, str]:
    """Exchange the active license for a device-scoped sync token.

    Re-registering always rotates the token on the Worker (license renewal hygiene).
    """
    from skyadmin_pro.services.net import require_https_api_url

    try:
        api_url = require_https_api_url(live_api_base_url())
    except RuntimeError:
        return (False, "Data sync requires a secure (https) API_BASE_URL in this build.")
    code = _license_code()
    if not code:
        return (False, "Activate a license before syncing data.")
    url = api_url.rstrip("/") + "/api/sync/register"
    payload = json.dumps({"code": code}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST", headers={"Content-Type": "application/json", "User-Agent": "SkyAdminPro"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            raw = resp.read(256 * 1024).decode("utf-8", errors="replace")
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            return (False, str(data.get("error") or f"HTTP {exc.code}"))
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            return (False, f"Sync registration failed (HTTP {exc.code}).")
    except (OSError, ValueError) as exc:
        return (False, f"Sync registration failed: {exc}")
    if not isinstance(data, dict) or not data.get("ok"):
        return (False, str((data or {}).get("error") or "Sync registration refused."))
    mid = str(data.get("machine_id") or get_machine_id()).strip().upper()
    token = str(data.get("sync_token") or "").strip()
    if not token:
        return (False, "Server did not return a sync token.")
    save_sync_credentials(mid, token)
    return (True, "Sync credentials registered.")


def rotate_sync_credentials_after_license_change(timeout: float = 10.0) -> tuple[bool, str]:
    """Rotate the device sync token after license renewal or replacement."""
    if load_sync_credentials() is None:
        return (True, "No sync credentials to rotate.")
    return register_sync_device(timeout=timeout)


def ensure_sync_credentials(timeout: float = 10.0) -> tuple[str, str] | None:
    creds = load_sync_credentials()
    if creds:
        return creds
    ok, _msg = register_sync_device(timeout=timeout)
    if not ok:
        return None
    return load_sync_credentials()
