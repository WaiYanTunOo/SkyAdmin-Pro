"""Lightweight performance guards for large client lists and dashboard queries."""

from __future__ import annotations

import sqlite3
import time
from datetime import date, timedelta

import pytest

from skyadmin_pro.config import SERVICE_TYPES
from skyadmin_pro.database import Database


@pytest.fixture
def populated_db(tmp_path) -> Database:
    db = Database(tmp_path / "perf.db")
    with db.connection() as conn:
        conn.executemany(
            "INSERT INTO clients (name, contact_name, email, status) VALUES (?, ?, ?, ?)",
            [(f"Client {index:04d}", f"Contact {index}", f"c{index}@example.com", "active") for index in range(500)],
        )
    return db


@pytest.fixture
def populated_tax_db(populated_db: Database) -> Database:
    db = populated_db
    service_type = SERVICE_TYPES[0]
    overdue = (date.today() - timedelta(days=7)).isoformat()
    current = date.today().isoformat()
    rows = []
    for index in range(500):
        client_id = index + 1
        rows.append(
            (
                client_id,
                service_type,
                overdue if index % 3 == 0 else current,
                0,
                "Ongoing" if index % 5 == 0 else "Completed",
            )
        )
    with db.connection() as conn:
        conn.executemany(
            """
            INSERT INTO documents (client_id, document_type, payment_date, paid, progress)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
    return db


@pytest.fixture
def query_stats():
    stats = {"connections": 0, "statements": 0}

    def attach(db: Database) -> None:
        original_get = db._get_pooled_conn

        def traced_get() -> sqlite3.Connection:
            stats["connections"] += 1
            conn = original_get()

            def trace(stmt: str) -> None:
                if stmt.lstrip().upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE", "WITH")):
                    stats["statements"] += 1

            conn.set_trace_callback(trace)
            return conn

        db._get_pooled_conn = traced_get  # type: ignore[method-assign]

    return stats, attach


def test_search_clients_handles_five_hundred_rows(populated_db):
    start = time.perf_counter()
    rows = populated_db.search_clients("")
    elapsed = time.perf_counter() - start
    assert len(rows) == 500
    assert elapsed < 0.75


def test_list_client_names_handles_five_hundred_rows(populated_db):
    start = time.perf_counter()
    names = populated_db.list_client_names()
    elapsed = time.perf_counter() - start
    assert len(names) == 500
    assert elapsed < 0.5


def test_list_overdue_services_handles_five_hundred_documents(populated_tax_db):
    start = time.perf_counter()
    rows = populated_tax_db.list_overdue_services()
    elapsed = time.perf_counter() - start
    assert len(rows) >= 100
    assert elapsed < 0.75


def test_dashboard_counts_uses_single_connection(populated_tax_db, query_stats):
    stats, attach = query_stats
    attach(populated_tax_db)
    counts = populated_tax_db.dashboard_counts(expiring_total=12)
    assert counts["clients"] == 500
    assert stats["connections"] == 1
    assert stats["statements"] <= 8


def test_dashboard_snapshot_query_budget(populated_tax_db, query_stats):
    stats, attach = query_stats
    attach(populated_tax_db)

    start = time.perf_counter()
    snap = populated_tax_db.dashboard_snapshot()
    elapsed = time.perf_counter() - start

    assert snap["counts"]["clients"] == 500
    assert len(snap["overdue"]) >= 100
    assert stats["connections"] <= 18
    assert stats["statements"] <= 40
    assert elapsed < 2.5


def test_perf_indexes_exist(populated_tax_db):
    names = {
        row["name"]
        for row in populated_tax_db._fetch_all(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_%'"
        )
    }
    assert "idx_documents_unpaid_overdue" in names
    assert "idx_documents_ongoing_service" in names
    assert "idx_supplier_payments_unpaid_due" in names
