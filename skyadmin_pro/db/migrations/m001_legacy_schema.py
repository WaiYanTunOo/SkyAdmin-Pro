"""Migration 001 — legacy schema upgrades for pre-release databases."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 1
NAME = "legacy_schema"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    db._migrate()
