"""Migration 003 — encrypt legacy plaintext IRD passwords."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 3
NAME = "secret_fields"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    db._migrate_secret_fields()
