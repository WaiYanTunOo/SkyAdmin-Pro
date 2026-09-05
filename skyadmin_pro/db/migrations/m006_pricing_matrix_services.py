"""Migration 006 — pricing_matrix service_type column."""

from __future__ import annotations

from typing import TYPE_CHECKING

VERSION = 6
NAME = "pricing_matrix_services"

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin


def upgrade(db: CoreMixin) -> None:
    """Add service_type column and unique (service_type, transaction_range)."""
    from skyadmin_pro.config import PRICING_DEFAULT_SERVICE

    with db.connection() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "pricing_matrix" not in tables:
            return
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(pricing_matrix)")}
        if "service_type" in columns:
            return
        conn.execute(
            """
            CREATE TABLE pricing_matrix_new (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                service_type        TEXT NOT NULL DEFAULT 'General',
                transaction_range   TEXT NOT NULL,
                monthly_fee         INTEGER,
                annual_fee          INTEGER,
                sla_hours           INTEGER,
                headcount           INTEGER,
                required_docs       TEXT,
                UNIQUE(service_type, transaction_range)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO pricing_matrix_new
                (id, service_type, transaction_range, monthly_fee, annual_fee,
                 sla_hours, headcount, required_docs)
            SELECT id, ?, transaction_range, monthly_fee, annual_fee,
                   sla_hours, headcount, required_docs
            FROM pricing_matrix
            """,
            (PRICING_DEFAULT_SERVICE,),
        )
        conn.execute("DROP TABLE pricing_matrix")
        conn.execute("ALTER TABLE pricing_matrix_new RENAME TO pricing_matrix")
    db._seed_all_service_pricing()
