"""Shared imports and helpers for data_sync chunks."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_SYNC_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def live_api_base_url() -> str:
    """Resolve at call time so patches on data_sync.API_BASE_URL are visible."""
    from skyadmin_pro.services import data_sync as sync_mod

    return sync_mod.API_BASE_URL or ""
