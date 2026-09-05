"""Migration 006 — pricing_matrix service_type column."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 6
NAME = "pricing_matrix_services"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    db._migrate_pricing_matrix_services()
