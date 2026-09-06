"""Per-table column visibility state — persisted in settings KV, no schema change.

Stored shape (forward-compatible with width persistence)::
    {"<table_id>": {"hidden": ["<col_id>", ...]}}

Parsing is tolerant: unknown tables/columns are ignored, corrupt payloads
fall back to empty. Width clamping lives here for the phase-2 width feature.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from skyadmin_pro.db.cipher import DB_ERRORS

if TYPE_CHECKING:
    from skyadmin_pro.database import Database

logger = logging.getLogger(__name__)

MIN_COLUMN_WIDTH = 40
MAX_COLUMN_WIDTH = 600


def _setting_key() -> str:
    from skyadmin_pro.config.tasks import SETTING_TABLE_COLUMNS

    return SETTING_TABLE_COLUMNS


def _load_all(db: Database) -> dict:
    try:
        raw = db.get_setting(_setting_key()) or ""
    except DB_ERRORS:
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("Ignoring corrupt table-columns setting", exc_info=True)
        return {}
    return data if isinstance(data, dict) else {}


def _save_all(db: Database, data: dict) -> None:
    try:
        db.set_setting(_setting_key(), json.dumps(data))
    except DB_ERRORS:
        logger.warning("Could not persist table-columns setting", exc_info=True)


def load_hidden_columns(db: Database, table_id: str) -> set[str]:
    """Hidden column ids for a table (unknown ids kept — caller intersects)."""
    entry = _load_all(db).get(table_id)
    if not isinstance(entry, dict):
        return set()
    hidden = entry.get("hidden", [])
    if not isinstance(hidden, list):
        return set()
    return {str(col) for col in hidden}


def save_hidden_columns(db: Database, table_id: str, hidden: list[str]) -> None:
    """Persist hidden column ids for a table (empty list clears)."""
    data = _load_all(db)
    data[table_id] = {"hidden": [str(col) for col in hidden]}
    _save_all(db, data)


def clamp_column_width(width: int) -> int:
    """Clamp a persisted column width into the sane range (phase-2 helper)."""
    try:
        return max(MIN_COLUMN_WIDTH, min(MAX_COLUMN_WIDTH, int(width)))
    except (TypeError, ValueError):
        return MIN_COLUMN_WIDTH
