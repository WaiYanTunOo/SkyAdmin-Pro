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
    # One pinned connection for the whole snapshot (bundle_queries).
    assert stats["connections"] == 1
    assert stats["statements"] <= 40
    assert elapsed < 2.5


def test_bundle_queries_nests_and_rolls_back(populated_db):
    db = populated_db
    with db.bundle_queries():
        db.get_or_create_client("Bundled Co")
        with db.bundle_queries():
            assert db.client_id_by_name("Bundled Co") is not None
    assert db.client_id_by_name("Bundled Co") is not None

    class _Boom(Exception):
        pass

    with pytest.raises(_Boom):
        with db.bundle_queries():
            db.get_or_create_client("Rollback Co")
            raise _Boom()
    assert db.client_id_by_name("Rollback Co") is None


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


@pytest.fixture
def large_tax_db(tmp_path) -> Database:
    """5000 clients + 5000 documents — large-client headroom guard."""
    db = Database(tmp_path / "perf_large.db")
    with db.connection() as conn:
        conn.executemany(
            "INSERT INTO clients (name, contact_name, email, status) VALUES (?, ?, ?, ?)",
            [(f"Big Client {i:05d}", f"Contact {i}", f"b{i}@example.com", "active") for i in range(5000)],
        )
    service_type = SERVICE_TYPES[0]
    overdue = (date.today() - timedelta(days=7)).isoformat()
    current = date.today().isoformat()
    with db.connection() as conn:
        conn.executemany(
            "INSERT INTO documents (client_id, document_type, payment_date, paid, progress) VALUES (?, ?, ?, ?, ?)",
            [
                (i + 1, service_type, overdue if i % 3 == 0 else current, 0, "Ongoing")
                for i in range(5000)
            ],
        )
    return db


def test_large_client_headroom(large_tax_db, query_stats):
    stats, attach = query_stats
    attach(large_tax_db)

    start = time.perf_counter()
    snap = large_tax_db.dashboard_snapshot()
    snapshot_elapsed = time.perf_counter() - start
    assert snap["counts"]["clients"] == 5000
    assert stats["connections"] == 1
    assert snapshot_elapsed < 1.5

    start = time.perf_counter()
    rows = large_tax_db.search_clients("Big Client 01")
    assert len(rows) >= 100
    assert time.perf_counter() - start < 1.0

    start = time.perf_counter()
    assert len(large_tax_db.list_clients()) == 5000
    assert time.perf_counter() - start < 1.0


def test_paged_lists_page1_under_budget_at_5k(large_tax_db):
    """P0/P3 gate: first page of every big list renders from <500ms of SQL."""
    db = large_tax_db
    budgets = {
        "clients": lambda: db.search_clients("", limit=251, offset=0),
        "tasks": lambda: db.list_tasks(limit=251, offset=0),
        "courier": lambda: db.list_courier_logs(limit=251, offset=0),
        "pipeline": lambda: db.list_pipeline_items(limit=251, offset=0),
        "documents": lambda: db.list_documents(limit=251, offset=0),
        "suppliers": lambda: db.list_suppliers(limit=251, offset=0),
    }
    for name, fn in budgets.items():
        start = time.perf_counter()
        rows = fn()
        elapsed = time.perf_counter() - start
        assert len(rows) <= 251, name
        assert elapsed < 0.5, f"{name} page-1 took {elapsed:.2f}s"


def test_client_names_cache_invalidates(populated_db):
    db = populated_db
    before = db.list_client_names()
    assert len(before) == 500
    db.get_or_create_client("Cache Probe Co")
    after = db.list_client_names()
    assert "Cache Probe Co" in after
    assert len(after) == 501
