from __future__ import annotations

from ..importer.funcs import Database
from ._common import *
from ._common import (
    SETTING_SYNC_LAST_PULL,
    SETTING_SYNC_LAST_PUSH,
    SYNC_PULL_MAX_PAGES,
    SYNC_PULL_PAGE_SIZE,
    SYNC_PUSH_PAGE_SIZE,
    Any,
    get_machine_id,
    live_api_base_url,
)
from .chunk_0 import _credentials_path
from .chunk_1 import ensure_sync_credentials
from .chunk_2 import _sync_request_with_retry
from .chunk_4 import collect_local_changes, is_data_sync_enabled
from .chunk_6 import apply_remote_changes, ensure_sync_ids


def sync_data(db: Database, *, timeout: float = 25.0) -> tuple[bool, str]:
    """Pull then push business data via the Worker sync API."""
    if not live_api_base_url().strip():
        return (True, "Data sync skipped (no API URL in this build).")
    if not is_data_sync_enabled(db):
        return (True, "Cloud data sync is off — use encrypted backup (.skybackup) to move data to another PC.")
    creds = ensure_sync_credentials(timeout=timeout)
    if not creds:
        return (False, "Could not register sync credentials — activate online first.")
    machine_id, token = creds
    if machine_id != get_machine_id().strip().upper():
        try:
            _credentials_path().unlink(missing_ok=True)
        except OSError:
            pass
        return (False, "Sync credentials are for a different machine ID — please re-activate.")
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
            "GET", "/api/sync/pull", machine_id=machine_id, token=token, query="&".join(query_parts), timeout=timeout
        )
        if not pull_ok:
            return (False, f"Pull failed: {pull_result}")
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
                return (False, "Sync protocol retired — install the latest SkyAdmin Pro build, then Sync Now again.")
            return (False, f"Push failed: {push_result}")
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
    if last_server_time:
        db.set_setting(SETTING_SYNC_LAST_PULL, last_server_time)
    conflicts = pull_conflicts + push_conflicts
    page_note = f" ({pages} pull page{('s' if pages != 1 else '')})" if pages > 1 else ""
    push_note = f" ({push_pages} push page{('s' if push_pages != 1 else '')})" if push_pages > 1 else ""
    msg = f"Data sync OK — pulled {pulled}{page_note}, pushed {total_applied}{push_note}."
    if conflicts:
        msg += f" {conflicts} conflict(s) logged."
    return (True, msg)
