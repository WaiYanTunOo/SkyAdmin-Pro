from __future__ import annotations

from ._common import (
    _SYNC_IDENT_RE,
    API_BASE_URL,
    DB_ERRORS,
    FK_CLIENT_COLUMN,
    FK_GROUP_COLUMN,
    INTEGRITY_ERRORS,
    SETTING_DATA_SYNC_ENABLED,
    SETTING_SYNC_LAST_PULL,
    SETTING_SYNC_LAST_PUSH,
    SYNC_ALLOWED_COLUMNS,
    SYNC_EXCLUDED_COLUMNS,
    SYNC_PULL_MAX_PAGES,
    SYNC_PULL_PAGE_SIZE,
    SYNC_PUSH_ORDER,
    SYNC_PUSH_PAGE_SIZE,
    SYNC_SCHEMA_VERSION,
    SYNC_TABLES,
    TYPE_CHECKING,
    Any,
    Path,
    __all__,
    annotations,
    find_license_file,
    get_machine_id,
    getpass,
    hlc_now,
    json,
    legacy_hlc,
    logger,
    logging,
    note_remote_hlc,
    os,
    parse_hlc,
    random,
    re,
    sys,
    time,
    urllib,
)
from .chunk_0 import _credentials_path, _license_code, load_sync_credentials, save_sync_credentials
from .chunk_1 import ensure_sync_credentials, register_sync_device, rotate_sync_credentials_after_license_change
from .chunk_2 import (
    _client_global_id,
    _client_id_for_global,
    _group_id_for_global,
    _sync_request,
    _sync_request_with_retry,
)
from .chunk_3 import _filter_sync_row, _parse_updated_at, _row_to_sync_payload, _sync_ident, _unique_group_name
from .chunk_4 import collect_local_changes, is_data_sync_enabled, log_sync_conflict
from .chunk_5 import _apply_remote_change
from .chunk_6 import apply_remote_changes, ensure_sync_ids
from .chunk_7 import sync_data

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
