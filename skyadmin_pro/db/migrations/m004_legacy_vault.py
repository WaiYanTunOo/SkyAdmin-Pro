"""Migration 004 — move vault_entries into credential tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 4
NAME = "legacy_vault"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    db._migrate_legacy_vault()
