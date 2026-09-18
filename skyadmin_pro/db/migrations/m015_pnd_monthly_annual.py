"""Migration 015 — PND monthly/annual status columns on clients.

Adds pnd1/pnd3 (monthly) and pnd90/pnd91 (annual) beside existing
pnd53/pp30/pnd50/pnd51 fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 15
NAME = "pnd_monthly_annual"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin

_NEW_COLS: tuple[tuple[str, str], ...] = (
    ("pnd1_status", "pnd1_status TEXT DEFAULT 'Not Applicable'"),
    ("pnd3_status", "pnd3_status TEXT DEFAULT 'Not Applicable'"),
    ("pnd90_status", "pnd90_status TEXT DEFAULT 'Not Applicable'"),
    ("pnd91_status", "pnd91_status TEXT DEFAULT 'Not Applicable'"),
)


def upgrade(db: CoreMixin) -> None:
    with db.connection() as conn:
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(clients)")}
        for name, ddl in _NEW_COLS:
            if name not in existing:
                conn.execute(f"ALTER TABLE clients ADD COLUMN {ddl}")
