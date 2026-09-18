"""Desktop sync table manifest — keep aligned with skyadmin-worker/src/sync_schema.ts."""

from __future__ import annotations

from ._const_0 import SYNC_SCHEMA_VERSION
from ._const_1 import SYNC_TABLES
from ._const_2 import SYNC_PUSH_ORDER
from ._const_3 import SYNC_PULL_PAGE_SIZE
from ._const_4 import SYNC_PULL_MAX_PAGES
from ._const_5 import SYNC_PUSH_PAGE_SIZE
from ._const_6 import FK_CLIENT_COLUMN
from ._const_7 import FK_GROUP_COLUMN
from ._const_8 import SYNC_EXCLUDED_COLUMNS
from ._const_9._const_0._const_0 import SYNC_ALLOWED_COLUMNS

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
]
