from __future__ import annotations

from ..importer.funcs import Database
from ._common import SETTING_SYNC_LAST_PULL, get_machine_id, live_api_base_url
from .chunk_0 import _credentials_path
from .chunk_1 import ensure_sync_credentials
from .chunk_4 import is_data_sync_enabled
from .chunk_6 import ensure_sync_ids
from .chunk_7_pull import _pull_remote_pages
from .chunk_7_push import push_local_pages
from .dirty import suppress_dirty
from .vault_status import vault_sync_status_note


def sync_data(db: Database, *, timeout: float = 25.0, mode: str = "full") -> tuple[bool, str]:
    """Pull and/or push business data via the Worker sync API.

    ``mode`` is ``full`` (default), ``pull``, or ``push``.
    """
    if mode not in ("full", "pull", "push"):
        mode = "full"
    if not live_api_base_url().strip():
        return (True, "Data sync skipped (no API URL in this build).")
    if not is_data_sync_enabled(db):
        return (True, "Cloud data sync is off — use encrypted backup (.skybackup) to move data to another PC.")
    with suppress_dirty():
        return _sync_data_inner(db, timeout=timeout, mode=mode)


def _sync_data_inner(db: Database, *, timeout: float, mode: str) -> tuple[bool, str]:
    creds, reg_err = ensure_sync_credentials(timeout=timeout, db=db)
    if not creds:
        return (False, reg_err or "Could not register sync credentials — activate online first.")
    machine_id, token = creds
    if machine_id != get_machine_id().strip().upper():
        try:
            _credentials_path().unlink(missing_ok=True)
        except OSError:
            pass
        return (False, "Sync credentials are for a different machine ID — please re-activate.")
    ensure_sync_ids(db)
    pulled = pull_conflicts = pages = 0
    last_server_time = ""
    if mode in ("full", "pull"):
        since = db.get_setting(SETTING_SYNC_LAST_PULL) or ""
        pulled, pull_conflicts, pull_data, pull_err, pages = _pull_remote_pages(
            db, machine_id=machine_id, token=token, timeout=timeout, since=since
        )
        if pull_err:
            return (False, pull_err)
        last_server_time = str(pull_data.get("server_time") or "")
    total_applied = push_conflicts = push_pages = 0
    vault_passwords = False
    if mode in ("full", "push"):
        total_applied, push_conflicts, push_pages, push_time, vault_passwords, push_err = push_local_pages(
            db, machine_id=machine_id, token=token, timeout=timeout
        )
        if push_err:
            return (False, push_err)
        if push_time:
            last_server_time = push_time
    if last_server_time and mode in ("full", "pull"):
        db.set_setting(SETTING_SYNC_LAST_PULL, last_server_time)
    conflicts = pull_conflicts + push_conflicts
    page_note = f" ({pages} pull page{('s' if pages != 1 else '')})" if pages > 1 else ""
    push_note = f" ({push_pages} push page{('s' if push_pages != 1 else '')})" if push_pages > 1 else ""
    msg = f"Data sync OK — pulled {pulled}{page_note}, pushed {total_applied}{push_note}."
    if conflicts:
        msg += f" {conflicts} conflict(s) logged."
    msg += vault_sync_status_note(db, vault_passwords)
    return (True, msg)
