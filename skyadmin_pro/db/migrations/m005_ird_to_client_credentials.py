"""Migration 005 — import IRD passwords into client_credentials."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 5
NAME = "ird_to_client_credentials"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    db._migrate_ird_to_client_credentials()
