"""Migration 007 — client_credentials login_id backfill."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 7
NAME = "client_credentials_login_id"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    db._migrate_client_credentials_login_id()
