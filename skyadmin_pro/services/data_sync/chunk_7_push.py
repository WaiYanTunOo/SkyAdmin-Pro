"""Push local sync-table changes to the Worker."""

from __future__ import annotations

from ..importer.funcs import Database
from ._common import (
    SETTING_SYNC_LAST_PUSH,
    SYNC_PULL_MAX_PAGES,
    SYNC_PUSH_PAGE_SIZE,
)
from .chunk_2 import _sync_request_with_retry
from .chunk_4_collect import collect_local_changes


def push_local_pages(
    db: Database, *, machine_id: str, token: str, timeout: float
) -> tuple[int, int, int, str, bool, str]:
    """Push pending local rows.

    Returns ``(applied, conflicts, pages, last_server_time, vault_passwords, error)``.
    """
    push_pages = 0
    total_applied = 0
    push_conflicts = 0
    push_since = db.get_setting(SETTING_SYNC_LAST_PUSH) or ""
    last_server_time = ""
    vault_passwords = False
    while push_pages < SYNC_PULL_MAX_PAGES:
        local_changes = collect_local_changes(db, since=push_since, limit=SYNC_PUSH_PAGE_SIZE)
        vault_passwords = vault_passwords or bool(getattr(collect_local_changes, "last_vault_passwords", False))
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
                    0,
                    0,
                    0,
                    "",
                    False,
                    "Sync protocol retired — install the latest SkyAdmin Pro build, then Sync Now again.",
                )
            return (0, 0, 0, "", False, f"Push failed: {push_result}")
        push_data = push_result if isinstance(push_result, dict) else {}
        server_time = str(push_data.get("server_time") or "")
        if server_time:
            last_server_time = server_time
        last_pushed_ua = str(local_changes[-1].get("updated_at") or "").strip()
        if not last_pushed_ua or last_pushed_ua == push_since:
            break
        push_since = last_pushed_ua
        db.set_setting(SETTING_SYNC_LAST_PUSH, push_since)
        total_applied += int(push_data.get("applied") or 0)
        push_conflicts += int(push_data.get("conflicts") or 0)
        if len(local_changes) < SYNC_PUSH_PAGE_SIZE:
            break
    return total_applied, push_conflicts, push_pages, last_server_time, vault_passwords, ""
