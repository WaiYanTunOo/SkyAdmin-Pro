"""Shared imports and helpers for data_sync chunks."""

from __future__ import annotations

import getpass
import json
import logging
import os
import random
import re
import sys
import time
import urllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skyadmin_pro.config import (
    API_BASE_URL,
    SETTING_DATA_SYNC_ENABLED,
    SETTING_SYNC_LAST_PULL,
    SETTING_SYNC_LAST_PUSH,
)
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
    pass

logger = logging.getLogger(__name__)

_SYNC_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")

# Explicit re-exports for chunk modules (`from ._common import *`) and package facade.
__all__ = [
    "API_BASE_URL",
    "Any",
    "DB_ERRORS",
    "FK_CLIENT_COLUMN",
    "FK_GROUP_COLUMN",
    "INTEGRITY_ERRORS",
    "Path",
    "SETTING_DATA_SYNC_ENABLED",
    "SETTING_SYNC_LAST_PULL",
    "SETTING_SYNC_LAST_PUSH",
    "SYNC_ALLOWED_COLUMNS",
    "SYNC_EXCLUDED_COLUMNS",
    "SYNC_PULL_MAX_PAGES",
    "SYNC_PULL_PAGE_SIZE",
    "SYNC_PUSH_ORDER",
    "SYNC_PUSH_PAGE_SIZE",
    "SYNC_SCHEMA_VERSION",
    "SYNC_TABLES",
    "_SYNC_IDENT_RE",
    "find_license_file",
    "get_machine_id",
    "getpass",
    "hlc_now",
    "json",
    "legacy_hlc",
    "live_api_base_url",
    "logger",
    "note_remote_hlc",
    "os",
    "parse_hlc",
    "random",
    "re",
    "sys",
    "time",
    "urllib",
]


def live_api_base_url() -> str:
    """Resolve at call time so patches on data_sync.API_BASE_URL are visible."""
    from skyadmin_pro.services import data_sync as sync_mod

    return sync_mod.API_BASE_URL or ""
