"""Migration 002 — assign sync global_id UUIDs."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 2
NAME = "backfill_sync_global_ids"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    db._backfill_sync_global_ids()
