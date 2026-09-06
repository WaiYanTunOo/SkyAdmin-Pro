"""P4 cross-device business data sync (Worker API)."""

from __future__ import annotations

import getpass
import json
import logging
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skyadmin_pro.config import API_BASE_URL, SETTING_DATA_SYNC_ENABLED, SETTING_SYNC_LAST_PULL, SETTING_SYNC_LAST_PUSH
from skyadmin_pro.db.cipher import DB_ERRORS, INTEGRITY_ERRORS
from skyadmin_pro.services.license import find_license_file, get_machine_id
from skyadmin_pro.services.sync_hlc import hlc_now, legacy_hlc, note_remote_hlc, parse_hlc
from skyadmin_pro.services.sync_schema import (
    FK_CLIENT_COLUMN,
    FK_GROUP_COLUMN,
    SYNC_ALLOWED_COLUMNS,
    SYNC_EXCLUDED_COLUMNS,
    SYNC_PULL_MAX_PAGES,
    SYNC_PULL_PAGE_SIZE,
    SYNC_PUSH_ORDER,
    SYNC_PUSH_PAGE_SIZE,
    SYNC_SCHEMA_VERSION,
    SYNC_TABLES,
)

if TYPE_CHECKING:
    from skyadmin_pro.database import Database

logger = logging.getLogger(__name__)

_SYNC_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")

# Re-export schema constants for callers/tests that import from data_sync.
__all__ = [
    "FK_CLIENT_COLUMN",
    "FK_GROUP_COLUMN",
    "SYNC_ALLOWED_COLUMNS",
    "SYNC_EXCLUDED_COLUMNS",
    "SYNC_PULL_MAX_PAGES",
    "SYNC_PULL_PAGE_SIZE",
    "SYNC_PUSH_ORDER",
    "SYNC_PUSH_PAGE_SIZE",
    "SYNC_SCHEMA_VERSION",
    "SYNC_TABLES",
    "apply_remote_changes",
    "collect_local_changes",
    "ensure_sync_ids",
    "is_data_sync_enabled",
    "log_sync_conflict",
    "sync_data",
]


def _credentials_path() -> Path:
    from skyadmin_pro.paths import app_data_dir

    return app_data_dir() / "sync_device.json"


def load_sync_credentials() -> tuple[str, str] | None:
    path = _credentials_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        from skyadmin_pro.services.secret_fields import decrypt_secret, is_encrypted_secret

        if is_encrypted_secret(raw):
            plain = decrypt_secret(raw)
            if not plain:
                logger.warning("sync_device.json decrypt failed (wrong machine?)", exc_info=False)
                return None
            data = json.loads(plain)
        else:
            data = json.loads(raw)
            mid = str(data.get("machine_id") or "").strip().upper()
            token = str(data.get("sync_token") or "").strip()
            if mid and token:
                save_sync_credentials(mid, token)
                return mid, token
            return None
        mid = str(data.get("machine_id") or "").strip().upper()
        token = str(data.get("sync_token") or "").strip()
        if mid and token:
            return mid, token
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("sync_device.json corrupt: %s", exc, exc_info=True)
        try:
            corrupt = path.with_suffix(".corrupt")
            if not corrupt.exists():
                path.rename(corrupt)
        except OSError:
            pass
    return None


def save_sync_credentials(machine_id: str, sync_token: str) -> None:
    from skyadmin_pro.services.secret_fields import encrypt_secret

    path = _credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {"machine_id": machine_id.strip().upper(), "sync_token": sync_token.strip()},
        ensure_ascii=False,
    )
    path.write_text(encrypt_secret(payload), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError as exc:
        logger.warning("Could not chmod %s: %s", path, exc)
    # Windows NTFS: chmod is no-op — restrict ACL to current user via icacls
    if sys.platform == "win32":
        try:
            import subprocess

            user = os.environ.get("USERNAME") or getpass.getuser()
            resolved_path = str(path)
            # Validate path is a real file/dir before calling icacls
            if not os.path.exists(resolved_path):
                return
            # Remove inheritance and grant only current user full control
            subprocess.run(
                ["icacls", resolved_path, "/inheritance:r", "/grant:r", f"{user}:(F)"],
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            logger.warning("Could not restrict ACL on %s: %s", path, exc)


def _license_code() -> str | None:
    path = find_license_file()
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
        return text or None
    except OSError:
        return None


def register_sync_device(timeout: float = 10.0) -> tuple[bool, str]:
    """Exchange the active license for a device-scoped sync token.

    Re-registering always rotates the token on the Worker (license renewal hygiene).
    """
    from skyadmin_pro.services.net import require_https_api_url

    try:
        api_url = require_https_api_url(API_BASE_URL or "")
    except RuntimeError:
        return False, "Data sync requires a secure (https) API_BASE_URL in this build."

    code = _license_code()
    if not code:
        return False, "Activate a license before syncing data."

    url = api_url.rstrip("/") + "/api/sync/register"
    payload = json.dumps({"code": code}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "SkyAdminPro"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(256 * 1024).decode("utf-8", errors="replace")
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            return False, str(data.get("error") or f"HTTP {exc.code}")
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            return False, f"Sync registration failed (HTTP {exc.code})."
    except (OSError, ValueError) as exc:
        return False, f"Sync registration failed: {exc}"

    if not isinstance(data, dict) or not data.get("ok"):
        return False, str((data or {}).get("error") or "Sync registration refused.")

    mid = str(data.get("machine_id") or get_machine_id()).strip().upper()
    token = str(data.get("sync_token") or "").strip()
    if not token:
        return False, "Server did not return a sync token."
    save_sync_credentials(mid, token)
    return True, "Sync credentials registered."


def rotate_sync_credentials_after_license_change(timeout: float = 10.0) -> tuple[bool, str]:
    """Rotate the device sync token after license renewal or replacement."""
    if load_sync_credentials() is None:
        return True, "No sync credentials to rotate."
    return register_sync_device(timeout=timeout)


def ensure_sync_credentials(timeout: float = 10.0) -> tuple[str, str] | None:
    creds = load_sync_credentials()
    if creds:
        return creds
    ok, _msg = register_sync_device(timeout=timeout)
    if not ok:
        return None
    return load_sync_credentials()


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
        api_url = require_https_api_url(API_BASE_URL or "")
    except RuntimeError:
        return False, "API_BASE_URL must use https:// (refusing insecure sync)."

    url = api_url.rstrip("/") + path
    if query:
        url += ("&" if "?" in url else "?") + query

    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Machine-Id": machine_id,
        "User-Agent": "SkyAdminPro",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(4 * 1024 * 1024).decode("utf-8", errors="replace")
            parsed = json.loads(raw)
            return True, parsed if isinstance(parsed, dict) else {}
    except urllib.error.HTTPError as exc:
        try:
            parsed = json.loads(exc.read().decode("utf-8", errors="replace"))
            if isinstance(parsed, dict):
                return False, str(parsed.get("error") or f"HTTP {exc.code}")
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            pass
        return False, f"Sync HTTP {exc.code}"
    except (OSError, ValueError) as exc:
        return False, str(exc)


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
    last_ok, last_err = False, "No attempts made"
    for attempt in range(retries):
        ok, result = _sync_request(
            method, path, machine_id=machine_id, token=token,
            body=body, query=query, timeout=timeout,
        )
        if ok:
            return True, result
        last_ok, last_err = ok, result
        err_str = str(result or "")
        retryable = err_str.startswith("Sync HTTP 5") or "timed out" in err_str.lower() or "urllib" in err_str.lower()
        if not retryable or attempt == retries - 1:
            break
        delay = min(2 ** attempt + random.uniform(0, 0.5), 8)
        logger.debug("Sync %s %s failed (attempt %d), retrying in %.1fs: %s", method, path, attempt + 1, delay, result)
        time.sleep(delay)
    return last_ok, last_err


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
    row = db._fetch_one(
        "SELECT id FROM client_groups WHERE global_id = ? AND deleted_at IS NULL",
        (str(global_id),),
    )
    return int(row["id"]) if row else None


def _unique_group_name(db: Database, name: str, global_id: str) -> str:
    """Avoid UNIQUE name collisions when two devices create the same label."""
    cleaned = (name or "").strip() or "Group"
    existing = db._fetch_one(
        """
        SELECT id, global_id FROM client_groups
        WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL
        """,
        (cleaned,),
    )
    if not existing:
        return cleaned
    if str(existing.get("global_id") or "") == global_id:
        return cleaned
    short = (global_id or "x")[:6]
    candidate = f"{cleaned} ({short})"
    clash = db._fetch_one(
        """
        SELECT id FROM client_groups
        WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL
          AND (global_id IS NULL OR global_id != ?)
        """,
        (candidate, global_id),
    )
    if not clash:
        return candidate
    return f"{cleaned} ({global_id[:12]})"


def _filter_sync_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    allowed = SYNC_ALLOWED_COLUMNS.get(table, frozenset())
    return {k: v for k, v in row.items() if k in allowed}


def _sync_ident(name: str) -> str:
    """Quote a table/column identifier for sync SQL.

    Trust assumption: every identifier passed here is an allowlisted constant —
    table names are validated against SYNC_TABLES and column names originate
    from SYNC_ALLOWED_COLUMNS (plus the internal remaps ``global_id``,
    ``updated_at``, ``client_id``, ``group_id``). Remote payload keys are
    filtered through _filter_sync_row before reaching SQL. Quoting is
    defense-in-depth; anything outside ``[A-Za-z_][A-Za-z0-9_]*`` raises.
    """
    text = str(name or "")
    if not _SYNC_IDENT_RE.match(text):
        raise ValueError(f"Refusing sync SQL identifier: {name!r}")
    return f'"{text}"'


def _parse_updated_at(value: str) -> float:
    """Parse an `updated_at` value to a UTC epoch for last-write-wins.

    Fleet convention: desktop writers stamp local-naive
    ``YYYY-MM-DD HH:MM:SS`` (``Database._now()`` / ``datetime('now',
    'localtime')``). Naive values are treated as UTC so ordering stays
    consistent across rows sharing the convention; values carrying an
    explicit zone (``Z`` or ``±HH:MM``) are honored exactly.
    Unparseable input returns 0.0 (loses LWW) instead of raising.
    """
    from datetime import datetime, timezone

    text = str(value or "").strip()
    if not text:
        return 0.0
    normalized = text.replace(" ", "T")
    try:
        if normalized.endswith(("Z", "z")):
            dt = datetime.fromisoformat(normalized[:-1] + "+00:00")
        elif len(normalized) >= 6 and normalized[-3] == ":" and normalized[-6] in "+-":
            dt = datetime.fromisoformat(normalized)
        else:
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).timestamp()
    except ValueError:
        logger.debug("Unparseable updated_at %r; falling back to epoch 0", value)
        return 0.0


def _row_to_sync_payload(db: Database, table: str, row: dict) -> dict[str, Any]:
    payload = dict(row)
    for col in SYNC_EXCLUDED_COLUMNS.get(table, frozenset()):
        payload.pop(col, None)
    if table in ("tasks", "office_contacts", "notebook_entries"):
        payload[FK_CLIENT_COLUMN] = _client_global_id(db, row.get("client_id"))
        payload.pop("client_id", None)
    if table == "clients":
        gid = row.get("group_id")
        if gid is not None:
            g_row = db._fetch_one(
                "SELECT global_id FROM client_groups WHERE id = ? AND deleted_at IS NULL",
                (int(gid),),
            )
            payload[FK_GROUP_COLUMN] = str(g_row["global_id"]) if g_row and g_row.get("global_id") else None
        else:
            payload[FK_GROUP_COLUMN] = None
        payload.pop("group_id", None)
    payload["global_id"] = str(row.get("global_id") or "")
    return payload


def is_data_sync_enabled(db: Database) -> bool:
    return (db.get_setting(SETTING_DATA_SYNC_ENABLED) or "0").strip() == "1"


def log_sync_conflict(
    db: Database,
    *,
    table: str,
    global_id: str,
    direction: str,
    local_updated_at: str | None,
    remote_updated_at: str | None,
    hlc_winner: str | None = None,
    hlc_loser: str | None = None,
) -> None:
    with db.connection() as conn:
        existing = conn.execute(
            """
            SELECT 1 FROM sync_conflicts
            WHERE table_name = ? AND global_id = ? AND direction = ?
            LIMIT 1
            """,
            (table, global_id, direction),
        ).fetchone()
        if existing:
            return
        conn.execute(
            """
            INSERT INTO sync_conflicts (table_name, global_id, direction, local_updated_at, remote_updated_at,
                                        hlc_winner, hlc_loser)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (table, global_id, direction, local_updated_at, remote_updated_at, hlc_winner, hlc_loser),
        )


def collect_local_changes(db: Database, *, since: str = "", limit: int | None = None) -> list[dict[str, Any]]:
    """Collect active rows and soft-delete tombstones for push (bounded globally)."""
    if limit is None:
        limit = SYNC_PUSH_PAGE_SIZE
    changes: list[dict[str, Any]] = []
    since = (since or "").strip()
    # Batch client / group global_id lookups for FK remapping
    client_gid_map: dict[int, str | None] = {}
    group_gid_map: dict[int, str | None] = {}
    try:
        for row in db._fetch_all("SELECT id, global_id FROM clients"):
            client_gid_map[int(row["id"])] = str(row["global_id"]) if row.get("global_id") else None
    except DB_ERRORS:
        logger.warning("Batch client GID lookup failed, using per-row fallback", exc_info=True)
        client_gid_map = {}
    try:
        for row in db._fetch_all("SELECT id, global_id FROM client_groups WHERE deleted_at IS NULL"):
            group_gid_map[int(row["id"])] = str(row["global_id"]) if row.get("global_id") else None
    except DB_ERRORS:
        logger.warning("Batch group GID lookup failed, using per-row fallback", exc_info=True)
        group_gid_map = {}
    for table in SYNC_PUSH_ORDER:
        t = _sync_ident(table)
        if since:
            rows = db._fetch_all(
                f"""
                SELECT * FROM {t}
                WHERE global_id IS NOT NULL AND TRIM(global_id) != ''
                  AND updated_at > ?
                ORDER BY updated_at ASC LIMIT ?
                """,
                (since, limit),
            )
        else:
            rows = db._fetch_all(
                f"SELECT * FROM {t} WHERE global_id IS NOT NULL AND TRIM(global_id) != '' ORDER BY updated_at ASC LIMIT ?",
                (limit,),
            )
        for row in rows:
            deleted_at = row.get("deleted_at")
            if deleted_at:
                row_payload = {"global_id": str(row["global_id"])}
            else:
                # Use batched maps to avoid per-row DB connection
                payload = dict(row)
                for col in SYNC_EXCLUDED_COLUMNS.get(table, frozenset()):
                    payload.pop(col, None)
                if table in ("tasks", "office_contacts", "notebook_entries"):
                    cid = row.get("client_id")
                    gid = client_gid_map.get(int(cid)) if cid is not None else None
                    payload[FK_CLIENT_COLUMN] = gid
                    payload.pop("client_id", None)
                if table == "clients":
                    local_gid = row.get("group_id")
                    payload[FK_GROUP_COLUMN] = group_gid_map.get(int(local_gid)) if local_gid is not None else None
                    payload.pop("group_id", None)
                payload = {
                    k: v
                    for k, v in payload.items()
                    if k in SYNC_ALLOWED_COLUMNS.get(table, frozenset())
                    or k
                    in (
                        "global_id",
                        "created_at",
                        "updated_at",
                        "deleted_at",
                        "hlc",
                        FK_CLIENT_COLUMN,
                        FK_GROUP_COLUMN,
                    )
                }
                payload["global_id"] = str(row.get("global_id") or "")
                row_payload = _filter_sync_row(table, payload)
                row_payload["global_id"] = str(row["global_id"])
            changes.append(
                {
                    "table": table,
                    "global_id": str(row["global_id"]),
                    "row": row_payload,
                    "updated_at": str(row.get("updated_at") or row.get("created_at") or ""),
                    "deleted_at": deleted_at,
                    # Phase 2: HLC stamped in updated_at order (see sync_hlc).
                    "hlc": hlc_now(db),
                    "proto": 2,
                }
            )

    # Sort globally by (updated_at, hlc) and strictly truncate to global limit
    changes.sort(key=lambda c: (c["updated_at"], c.get("hlc") or ""))
    return changes[:limit]


def _apply_remote_change(db: Database, change: dict[str, Any]) -> str:
    """Apply one remote change. Returns 'applied', 'skipped', or 'invalid'.

    Phase 2 merge: when both sides carry a valid HLC the clocks decide
    (total order — ties impossible); otherwise the legacy updated_at
    comparison applies. Either way the incoming HLC, when valid, is stored
    and the local clock fast-forwards past it.
    """
    table = str(change.get("table") or "")
    global_id = str(change.get("global_id") or "").strip()
    updated_at = str(change.get("updated_at") or "").strip()
    if table not in SYNC_TABLES or not global_id or not updated_at:
        return "invalid"

    remote_hlc = parse_hlc(change.get("hlc"))
    local = db._fetch_one(
        f"SELECT id, updated_at, hlc FROM {_sync_ident(table)} WHERE global_id = ?",
        (global_id,),
    )
    local_hlc = None
    if local:
        local_hlc = parse_hlc(local.get("hlc")) or legacy_hlc(str(local.get("updated_at") or ""))
    if local and (
        (remote_hlc is not None and local_hlc is not None and remote_hlc <= local_hlc)
        or (
            (remote_hlc is None or local_hlc is None)
            and _parse_updated_at(str(local.get("updated_at") or "")) >= _parse_updated_at(updated_at)
        )
    ):
        local_hlc_str = local.get("hlc") if isinstance(local.get("hlc"), str) else None
        log_sync_conflict(
            db,
            table=table,
            global_id=global_id,
            direction="pull",
            local_updated_at=str(local.get("updated_at") or ""),
            remote_updated_at=updated_at,
            hlc_winner=local_hlc_str,
            hlc_loser=str(change.get("hlc") or ""),
        )
        if remote_hlc is not None:
            note_remote_hlc(db, change.get("hlc"))
        return "skipped"
    if remote_hlc is not None:
        note_remote_hlc(db, change.get("hlc"))

    if change.get("deleted_at"):
        if local:
            t = _sync_ident(table)
            with db.connection() as conn:
                if remote_hlc is not None:
                    conn.execute(
                        f"UPDATE {t} SET deleted_at = ?, updated_at = ?, hlc = ? WHERE global_id = ?",
                        (change.get("deleted_at"), updated_at, str(change.get("hlc")), global_id),
                    )
                else:
                    conn.execute(
                        f"UPDATE {t} SET deleted_at = ?, updated_at = ? WHERE global_id = ?",
                        (change.get("deleted_at"), updated_at, global_id),
                    )
            if table == "client_groups":
                local_id = int(local["id"])
                with db.connection() as conn:
                    conn.execute(
                        "UPDATE clients SET group_id = NULL WHERE group_id = ?",
                        (local_id,),
                    )
        return "applied"

    row = _filter_sync_row(table, dict(change.get("row") or {}))
    row["global_id"] = global_id
    row["updated_at"] = updated_at
    row.pop("deleted_at", None)
    if remote_hlc is not None:
        row["hlc"] = str(change.get("hlc"))

    if table in ("tasks", "office_contacts", "notebook_entries"):
        client_gid = row.pop(FK_CLIENT_COLUMN, None) or row.pop("client_global_id", None)
        row["client_id"] = _client_id_for_global(db, str(client_gid) if client_gid else None)

    if table == "clients":
        group_gid = row.pop(FK_GROUP_COLUMN, None) or row.pop("group_global_id", None)
        row.pop("group_id", None)
        row["group_id"] = _group_id_for_global(db, str(group_gid) if group_gid else None)

    if table == "client_groups" and "name" in row:
        row["name"] = _unique_group_name(db, str(row.get("name") or ""), global_id)

    if not row or (len(row) <= 2 and not change.get("deleted_at")):
        return "invalid"

    if local:
        cols = [k for k in row if k != "global_id"]
        if not cols:
            return "invalid"
        assignments = ", ".join(f"{_sync_ident(col)} = ?" for col in cols)
        values = [row[col] for col in cols] + [global_id]
        with db.connection() as conn:
            conn.execute(f"UPDATE {_sync_ident(table)} SET {assignments} WHERE global_id = ?", values)
        return "applied"

    cols = list(row.keys())
    col_list = ", ".join(_sync_ident(c) for c in cols)
    placeholders = ", ".join("?" for _ in cols)
    try:
        with db.connection() as conn:
            conn.execute(
                f"INSERT INTO {_sync_ident(table)} ({col_list}) VALUES ({placeholders})",
                [row[col] for col in cols],
            )
    except INTEGRITY_ERRORS:
        if table != "client_groups" or "name" not in row:
            raise
        row["name"] = _unique_group_name(db, f"{row.get('name')}*", global_id)
        with db.connection() as conn:
            conn.execute(
                f"INSERT INTO {_sync_ident(table)} ({col_list}) VALUES ({placeholders})",
                [row[col] for col in cols],
            )
    return "applied"


def apply_remote_changes(db: Database, changes: list[dict[str, Any]]) -> tuple[int, int]:
    applied = 0
    conflicts = 0
    # Apply deletes child-first (reverse order) to avoid FK orphan, inserts parent-first
    deletes = [c for c in changes if c.get("deleted_at")]
    upserts = [c for c in changes if not c.get("deleted_at")]
    deletes_ordered = sorted(
        deletes, key=lambda c: -(SYNC_PUSH_ORDER.index(c["table"]) if c.get("table") in SYNC_PUSH_ORDER else -99)
    )
    upserts_ordered = sorted(
        upserts, key=lambda c: SYNC_PUSH_ORDER.index(c["table"]) if c.get("table") in SYNC_PUSH_ORDER else 99
    )
    # One transaction per pull page: bundle_queries() pins a single connection
    # so inner connection() checkouts reuse it with one commit on clean exit
    # (rollback on error) instead of one connection/commit per row.
    opener = getattr(db, "bundle_queries", None) or db.connection
    with opener():
        for change in deletes_ordered + upserts_ordered:
            result = _apply_remote_change(db, change)
            if result == "applied":
                applied += 1
            elif result == "skipped":
                conflicts += 1
    return applied, conflicts


def ensure_sync_ids(db: Database) -> None:
    """Assign global_id to any rows missing one before push."""
    import uuid

    with db.connection() as conn:
        for table in SYNC_TABLES:
            t = _sync_ident(table)
            rows = conn.execute(f"SELECT id FROM {t} WHERE global_id IS NULL OR TRIM(global_id) = ''").fetchall()
            for row in rows:
                conn.execute(
                    f"UPDATE {t} SET global_id = ? WHERE id = ?",
                    (uuid.uuid4().hex, int(row["id"])),
                )


def sync_data(db: Database, *, timeout: float = 25.0) -> tuple[bool, str]:
    """Pull then push business data via the Worker sync API."""
    if not (API_BASE_URL or "").strip():
        return True, "Data sync skipped (no API URL in this build)."
    if not is_data_sync_enabled(db):
        return True, "Cloud data sync is off — use encrypted backup (.skybackup) to move data to another PC."

    creds = ensure_sync_credentials(timeout=timeout)
    if not creds:
        return False, "Could not register sync credentials — activate online first."

    machine_id, token = creds
    if machine_id != get_machine_id().strip().upper():
        # Stale credentials — remove and prompt re-register
        try:
            _credentials_path().unlink(missing_ok=True)
        except OSError:
            pass
        return False, "Sync credentials are for a different machine ID — please re-activate."

    ensure_sync_ids(db)

    since = db.get_setting(SETTING_SYNC_LAST_PULL) or ""
    pulled = 0
    pull_conflicts = 0
    pages = 0
    pull_data: dict[str, Any] = {}
    while pages < SYNC_PULL_MAX_PAGES:
        pages += 1
        query_parts = [f"limit={SYNC_PULL_PAGE_SIZE}"]
        if since:
            query_parts.insert(0, f"since={urllib.parse.quote(str(since))}")
        pull_ok, pull_result = _sync_request_with_retry(
            "GET",
            "/api/sync/pull",
            machine_id=machine_id,
            token=token,
            query="&".join(query_parts),
            timeout=timeout,
        )
        if not pull_ok:
            return False, f"Pull failed: {pull_result}"

        pull_data = pull_result if isinstance(pull_result, dict) else {}
        changes = pull_data.get("changes") or []
        if not isinstance(changes, list) or not changes:
            break

        page_pulled, page_conflicts = apply_remote_changes(db, changes)
        pulled += page_pulled
        pull_conflicts += page_conflicts

        if len(changes) < SYNC_PULL_PAGE_SIZE:
            break
        last_ua = str(changes[-1].get("updated_at") or "").strip()
        if not last_ua or last_ua == since:
            break
        since = last_ua

    push_pages = 0
    total_applied = 0
    push_conflicts = 0
    push_since = db.get_setting(SETTING_SYNC_LAST_PUSH) or ""
    # Pull watermark stays on Worker server_time; push cursor tracks local updated_at.
    last_server_time = str(pull_data.get("server_time") or "")

    while push_pages < SYNC_PULL_MAX_PAGES:
        local_changes = collect_local_changes(db, since=push_since, limit=SYNC_PUSH_PAGE_SIZE)
        if not local_changes:
            break

        push_pages += 1
        push_ok, push_result = _sync_request_with_retry(
            "POST",
            "/api/sync/push",
            machine_id=machine_id,
            token=token,
            body={"changes": local_changes},
            timeout=timeout,
        )
        if not push_ok:
            if "upgrade-required" in str(push_result):
                return (
                    False,
                    "Sync protocol retired — install the latest SkyAdmin Pro build, then Sync Now again.",
                )
            return False, f"Push failed: {push_result}"

        push_data = push_result if isinstance(push_result, dict) else {}
        server_time = str(push_data.get("server_time") or "")
        if server_time:
            last_server_time = server_time

        last_pushed_ua = str(local_changes[-1].get("updated_at") or "").strip()
        if not last_pushed_ua or last_pushed_ua == push_since:
            break

        # Persist local updated_at so the next sync/page continues without skipping.
        push_since = last_pushed_ua
        db.set_setting(SETTING_SYNC_LAST_PUSH, push_since)

        total_applied += int(push_data.get("applied") or 0)
        push_conflicts += int(push_data.get("conflicts") or 0)

        if len(local_changes) < SYNC_PUSH_PAGE_SIZE:
            break

    if last_server_time:
        db.set_setting(SETTING_SYNC_LAST_PULL, last_server_time)

    conflicts = pull_conflicts + push_conflicts
    page_note = f" ({pages} pull page{'s' if pages != 1 else ''})" if pages > 1 else ""
    push_note = f" ({push_pages} push page{'s' if push_pages != 1 else ''})" if push_pages > 1 else ""
    msg = f"Data sync OK — pulled {pulled}{page_note}, pushed {total_applied}{push_note}."
    if conflicts:
        msg += f" {conflicts} conflict(s) logged."
    return True, msg
