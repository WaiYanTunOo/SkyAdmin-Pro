from __future__ import annotations

from ..importer.funcs import Database
from ._common import *
from ._common import live_api_base_url, logger, random


def _sync_request(
    method: str,
    path: str,
    *,
    machine_id: str,
    token: str,
    body: dict | None = None,
    query: str = "",
    timeout: float = 20.0,
) -> tuple[bool, dict | str]:
    from skyadmin_pro.services.net import require_https_api_url

    try:
        api_url = require_https_api_url(live_api_base_url())
    except RuntimeError:
        return (False, "API_BASE_URL must use https:// (refusing insecure sync).")
    url = api_url.rstrip("/") + path
    if query:
        url += ("&" if "?" in url else "?") + query
    data = None
    headers = {"Authorization": f"Bearer {token}", "X-Machine-Id": machine_id, "User-Agent": "SkyAdminPro"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            raw = resp.read(4 * 1024 * 1024).decode("utf-8", errors="replace")
            parsed = json.loads(raw)
            return (True, parsed if isinstance(parsed, dict) else {})
    except urllib.error.HTTPError as exc:
        try:
            parsed = json.loads(exc.read().decode("utf-8", errors="replace"))
            if isinstance(parsed, dict):
                return (False, str(parsed.get("error") or f"HTTP {exc.code}"))
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            pass
        return (False, f"Sync HTTP {exc.code}")
    except (OSError, ValueError) as exc:
        return (False, str(exc))


def _sync_request_with_retry(
    method: str,
    path: str,
    *,
    machine_id: str,
    token: str,
    body: dict | None = None,
    query: str = "",
    timeout: float = 20.0,
    retries: int = 3,
) -> tuple[bool, dict | str]:
    """Retry transient network / 5xx failures with exponential backoff."""
    last_ok, last_err = (False, "No attempts made")
    for attempt in range(retries):
        ok, result = _sync_request(
            method, path, machine_id=machine_id, token=token, body=body, query=query, timeout=timeout
        )
        if ok:
            return (True, result)
        last_ok, last_err = (ok, result)
        err_str = str(result or "")
        retryable = err_str.startswith("Sync HTTP 5") or "timed out" in err_str.lower() or "urllib" in err_str.lower()
        if not retryable or attempt == retries - 1:
            break
        delay = min(2**attempt + random.uniform(0, 0.5), 8)
        logger.debug("Sync %s %s failed (attempt %d), retrying in %.1fs: %s", method, path, attempt + 1, delay, result)
        time.sleep(delay)
    return (last_ok, last_err)


def _client_global_id(db: Database, client_id: int | None) -> str | None:
    if not client_id:
        return None
    row = db._fetch_one("SELECT global_id FROM clients WHERE id = ?", (int(client_id),))
    return str(row["global_id"]) if row and row.get("global_id") else None


def _client_id_for_global(db: Database, global_id: str | None) -> int | None:
    if not global_id:
        return None
    row = db._fetch_one("SELECT id FROM clients WHERE global_id = ?", (str(global_id),))
    return int(row["id"]) if row else None


def _group_id_for_global(db: Database, global_id: str | None) -> int | None:
    if not global_id:
        return None
    row = db._fetch_one("SELECT id FROM client_groups WHERE global_id = ? AND deleted_at IS NULL", (str(global_id),))
    return int(row["id"]) if row else None
