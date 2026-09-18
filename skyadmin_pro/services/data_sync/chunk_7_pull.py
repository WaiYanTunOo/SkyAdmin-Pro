from __future__ import annotations

from ..importer.funcs import Database
from ._common import SYNC_PULL_MAX_PAGES, SYNC_PULL_PAGE_SIZE, Any
from .chunk_2 import _sync_request_with_retry
from .chunk_6 import apply_remote_changes


def _pull_remote_pages(
    db: Database, *, machine_id: str, token: str, timeout: float, since: str
) -> tuple[int, int, dict[str, Any], str, int]:
    import urllib.parse

    pulled = 0
    pull_conflicts = 0
    pages = 0
    pull_data: dict[str, Any] = {}
    cursor = since
    while pages < SYNC_PULL_MAX_PAGES:
        pages += 1
        query_parts = [f"limit={SYNC_PULL_PAGE_SIZE}"]
        if cursor:
            query_parts.insert(0, f"since={urllib.parse.quote(str(cursor))}")
        pull_ok, pull_result = _sync_request_with_retry(
            "GET", "/api/sync/pull", machine_id=machine_id, token=token, query="&".join(query_parts), timeout=timeout
        )
        if not pull_ok:
            return (-1, 0, {}, f"Pull failed: {pull_result}", 0)
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
        if not last_ua or last_ua == cursor:
            break
        cursor = last_ua
    return pulled, pull_conflicts, pull_data, "", pages
