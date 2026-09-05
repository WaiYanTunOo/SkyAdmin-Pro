"""P4 cross-device business data sync (Worker API)."""

from __future__ import annotations

import getpass
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skyadmin_pro.config import API_BASE_URL, SETTING_DATA_SYNC_ENABLED, SETTING_SYNC_LAST_PULL, SETTING_SYNC_LAST_PUSH
from skyadmin_pro.services.license import find_license_file, get_machine_id

if TYPE_CHECKING:
    from skyadmin_pro.database import Database

logger = logging.getLogger(__name__)

SYNC_SCHEMA_VERSION = 1
SYNC_TABLES: tuple[str, ...] = ("clients", "tasks", "office_contacts", "notebook_entries")
SYNC_PUSH_ORDER: tuple[str, ...] = SYNC_TABLES

FK_CLIENT_COLUMN = "client_global_id"

SYNC_EXCLUDED_COLUMNS: dict[str, frozenset[str]] = {
    "clients": frozenset({"ird_password", "id"}),
    "tasks": frozenset({"id"}),
    "office_contacts": frozenset({"id"}),
    "notebook_entries": frozenset({"id"}),
}

SYNC_ALLOWED_COLUMNS: dict[str, frozenset[str]] = {
    "clients": frozenset(
        {
            "name",
            "company_name",
            "contact_name",
            "email",
            "status",
            "notes",
            "registration_number",
            "director",
            "contact_number",
            "registered_capital",
            "vat_registration",
            "business_address",
            "business_objectives",
            "tax_id",
            "vat_registered",
            "vat_registered_date",
            "service_type",
            "num_transactions",
            "service_fee",
            "payment_status",
            "sla",
            "headcount",
            "fs_status",
            "pnd53_status",
            "pp30_status",
            "pnd51_status",
            "pnd50_status",
            "audit_status",
            "vo_address",
            "vo_service_provider",
            "vo_renewal_date",
            "csh_service_provider",
            "csh_renewal_date",
            "shareholder_info",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
        }
    ),
    "tasks": frozenset(
        {
            "title",
            "description",
            "status",
            "category",
            "due_date",
            "completed_at",
            "pipeline_item_id",
            "pipeline_step",
            "source_document_id",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            FK_CLIENT_COLUMN,
        }
    ),
    "office_contacts": frozenset(
        {
            "name",
            "role_title",
            "organization",
            "department",
            "phone",
            "email",
            "line_id",
            "category",
            "notes",
            "is_favorite",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            FK_CLIENT_COLUMN,
        }
    ),
    "notebook_entries": frozenset(
        {
            "entry_type",
            "title",
            "body",
            "entry_date",
            "author",
            "follow_up_date",
            "is_pinned",
            "global_id",
            "created_at",
            "updated_at",
            "deleted_at",
            FK_CLIENT_COLUMN,
        }
    ),
}


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
    except Exception:
        pass
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
        except Exception:
            pass


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
    except Exception as exc:
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
    except Exception as exc:
        return False, str(exc)


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


def _filter_sync_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    allowed = SYNC_ALLOWED_COLUMNS.get(table, frozenset())
    return {k: v for k, v in row.items() if k in allowed}


def _parse_updated_at(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    from datetime import datetime, timezone

    normalized = text.replace(" ", "T")
    # Treat DB timestamps as UTC if no explicit zone (SQLite datetime('now') is UTC)
    if not normalized.endswith("Z") and "+" not in normalized and normalized.count("-") <= 2:
        # No timezone info — assume UTC
        if "T" in normalized and normalized[-3] != ":" and normalized[-6] != "+" or "T" not in normalized:
            normalized = f"{normalized}Z"
    else:
        if not normalized.endswith("Z") and "+" not in normalized:
            normalized = f"{normalized}Z"
    try:
        dt = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).timestamp()
    except ValueError:
        return 0.0


def _row_to_sync_payload(db: Database, table: str, row: dict) -> dict[str, Any]:
    payload = dict(row)
    for col in SYNC_EXCLUDED_COLUMNS.get(table, frozenset()):
        payload.pop(col, None)
    if table in ("tasks", "office_contacts", "notebook_entries"):
        payload[FK_CLIENT_COLUMN] = _client_global_id(db, row.get("client_id"))
        payload.pop("client_id", None)
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
            INSERT INTO sync_conflicts (table_name, global_id, direction, local_updated_at, remote_updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (table, global_id, direction, local_updated_at, remote_updated_at),
        )


def collect_local_changes(db: Database, *, since: str = "", limit: int = 500) -> list[dict[str, Any]]:
    """Collect active rows and soft-delete tombstones for push (bounded)."""
    changes: list[dict[str, Any]] = []
    since = (since or "").strip()
    # Batch client global_id lookup for tasks/office_contacts/notebook_entries
    client_gid_map: dict[int, str | None] = {}
    try:
        for row in db._fetch_all("SELECT id, global_id FROM clients"):
            client_gid_map[int(row["id"])] = str(row["global_id"]) if row.get("global_id") else None
    except Exception:
        logger.warning("Batch client GID lookup failed, using per-row fallback", exc_info=True)
        client_gid_map = {}
    for table in SYNC_PUSH_ORDER:
        if since:
            rows = db._fetch_all(
                f"""
                SELECT * FROM {table}
                WHERE global_id IS NOT NULL AND TRIM(global_id) != ''
                  AND updated_at > ?
                ORDER BY updated_at ASC LIMIT ?
                """,
                (since, limit),
            )
        else:
            rows = db._fetch_all(
                f"SELECT * FROM {table} WHERE global_id IS NOT NULL AND TRIM(global_id) != '' ORDER BY updated_at ASC LIMIT ?",
                (limit,),
            )
        for row in rows:
            deleted_at = row.get("deleted_at")
            if deleted_at:
                row_payload = {"global_id": str(row["global_id"])}
            else:
                # Use batched client_gid_map to avoid per-row DB connection
                payload = dict(row)
                for col in SYNC_EXCLUDED_COLUMNS.get(table, frozenset()):
                    payload.pop(col, None)
                if table in ("tasks", "office_contacts", "notebook_entries"):
                    cid = row.get("client_id")
                    gid = client_gid_map.get(int(cid)) if cid is not None else None
                    payload[FK_CLIENT_COLUMN] = gid
                    payload.pop("client_id", None)
                payload = {
                    k: v
                    for k, v in payload.items()
                    if k in SYNC_ALLOWED_COLUMNS.get(table, frozenset())
                    or k in ("global_id", "created_at", "updated_at", "deleted_at", FK_CLIENT_COLUMN)
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
                }
            )
    return changes


def _apply_remote_change(db: Database, change: dict[str, Any]) -> str:
    """Apply one remote change. Returns 'applied', 'skipped', or 'invalid'."""
    table = str(change.get("table") or "")
    global_id = str(change.get("global_id") or "").strip()
    updated_at = str(change.get("updated_at") or "").strip()
    if table not in SYNC_TABLES or not global_id or not updated_at:
        return "invalid"

    local = db._fetch_one(
        f"SELECT id, updated_at FROM {table} WHERE global_id = ?",
        (global_id,),
    )
    if local and _parse_updated_at(str(local.get("updated_at") or "")) >= _parse_updated_at(updated_at):
        log_sync_conflict(
            db,
            table=table,
            global_id=global_id,
            direction="pull",
            local_updated_at=str(local.get("updated_at") or ""),
            remote_updated_at=updated_at,
        )
        return "skipped"

    if change.get("deleted_at"):
        if local:
            with db.connection() as conn:
                conn.execute(
                    f"UPDATE {table} SET deleted_at = ?, updated_at = ? WHERE global_id = ?",
                    (change.get("deleted_at"), updated_at, global_id),
                )
        return "applied"

    row = _filter_sync_row(table, dict(change.get("row") or {}))
    row["global_id"] = global_id
    row["updated_at"] = updated_at
    row.pop("deleted_at", None)

    if table in ("tasks", "office_contacts", "notebook_entries"):
        client_gid = row.pop(FK_CLIENT_COLUMN, None) or row.pop("client_global_id", None)
        row["client_id"] = _client_id_for_global(db, str(client_gid) if client_gid else None)

    if not row or (len(row) <= 2 and not change.get("deleted_at")):
        return "invalid"

    if local:
        cols = [k for k in row.keys() if k != "global_id"]
        if not cols:
            return "invalid"
        assignments = ", ".join(f"{col} = ?" for col in cols)
        values = [row[col] for col in cols] + [global_id]
        with db.connection() as conn:
            conn.execute(f"UPDATE {table} SET {assignments} WHERE global_id = ?", values)
        return "applied"

    cols = list(row.keys())
    placeholders = ", ".join("?" for _ in cols)
    with db.connection() as conn:
        conn.execute(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
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
            rows = conn.execute(f"SELECT id FROM {table} WHERE global_id IS NULL OR TRIM(global_id) = ''").fetchall()
            for row in rows:
                conn.execute(
                    f"UPDATE {table} SET global_id = ? WHERE id = ?",
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
        except Exception:
            pass
        return False, "Sync credentials are for a different machine ID — please re-activate."

    ensure_sync_ids(db)

    since = db.get_setting(SETTING_SYNC_LAST_PULL) or ""
    pull_ok, pull_result = _sync_request(
        "GET",
        "/api/sync/pull",
        machine_id=machine_id,
        token=token,
        query=f"since={urllib.parse.quote(since)}" if since else "",
        timeout=timeout,
    )
    if not pull_ok:
        return False, f"Pull failed: {pull_result}"

    pull_data = pull_result if isinstance(pull_result, dict) else {}
    changes = pull_data.get("changes") or []
    pulled = 0
    pull_conflicts = 0
    if isinstance(changes, list):
        pulled, pull_conflicts = apply_remote_changes(db, changes)

    local_changes = collect_local_changes(db, since=db.get_setting(SETTING_SYNC_LAST_PUSH) or "")
    push_ok, push_result = _sync_request(
        "POST",
        "/api/sync/push",
        machine_id=machine_id,
        token=token,
        body={"changes": local_changes},
        timeout=timeout,
    )
    if not push_ok:
        return False, f"Push failed: {push_result}"

    push_data = push_result if isinstance(push_result, dict) else {}
    server_time = str(pull_data.get("server_time") or push_data.get("server_time") or "")
    if server_time:
        db.set_setting(SETTING_SYNC_LAST_PULL, server_time)
        # Always advance push cursor on successful push (avoid infinite re-push of rejected changes)
        db.set_setting(SETTING_SYNC_LAST_PUSH, server_time)

    applied = int(push_data.get("applied") or 0)
    push_conflicts = int(push_data.get("conflicts") or 0)
    conflicts = pull_conflicts + push_conflicts
    msg = f"Data sync OK — pulled {pulled}, pushed {applied}."
    if conflicts:
        msg += f" {conflicts} conflict(s) logged."
    return True, msg
