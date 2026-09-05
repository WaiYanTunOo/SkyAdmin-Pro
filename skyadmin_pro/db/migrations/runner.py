"""Versioned SQLite migrations for SkyAdmin Pro."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skyadmin_pro.db.core import CoreMixin

MigrationFn = Callable[["CoreMixin"], None]

MIGRATIONS: Sequence[tuple[int, str, MigrationFn]] = ()


def register_migrations(items: Sequence[tuple[int, str, MigrationFn]]) -> None:
    global MIGRATIONS
    MIGRATIONS = tuple(sorted(items, key=lambda item: item[0]))


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            applied_at  TEXT NOT NULL
        )
        """
    )


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    _ensure_table(conn)
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {int(row[0]) for row in rows}


def _record(conn: sqlite3.Connection, version: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
        (version, name, datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )


def run_pending_migrations(
    db: CoreMixin,
    *,
    min_version: int | None = None,
    max_version: int | None = None,
) -> None:
    """Apply numbered migrations that are not yet recorded."""
    with db.connection() as conn:
        applied = _applied_versions(conn)

    for version, name, upgrade in MIGRATIONS:
        if min_version is not None and version < min_version:
            continue
        if max_version is not None and version > max_version:
            continue
        if version in applied:
            continue
        upgrade(db)
        with db.connection() as conn:
            _record(conn, version, name)
        applied.add(version)
