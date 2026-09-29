"""Tests for SkyAgent read-only DB wrapper."""

from __future__ import annotations

import sqlite3

import pytest

from skyadmin_pro.services.skyagent.exceptions import DatabaseReadOnlyError
from skyadmin_pro.services.skyagent.readonly import SkyAgentDB


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database with test data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            contact_name TEXT,
            email TEXT,
            status TEXT,
            service_type TEXT,
            payment_status TEXT,
            tax_id TEXT,
            created_at TEXT,
            deleted_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            client_id INTEGER,
            title TEXT,
            status TEXT,
            category TEXT,
            due_date TEXT,
            deleted_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            client_id INTEGER,
            document_type TEXT,
            expiry_date TEXT,
            payment_date TEXT,
            amount REAL,
            paid INTEGER,
            file_name TEXT,
            deleted_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE pipeline_items (
            id INTEGER PRIMARY KEY,
            client_id INTEGER,
            service TEXT,
            step INTEGER,
            step_date TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT,
            deleted_at TEXT
        )
    """)
    conn.execute(
        "INSERT INTO clients VALUES (1, 'ABC Corp', 'John', 'john@abc.com', 'active', 'accounting', 'paid', 'TAX001', '2024-01-01', NULL)"
    )
    conn.execute(
        "INSERT INTO clients VALUES (2, 'XYZ Ltd', 'Jane', 'jane@xyz.com', 'active', 'tax', 'pending', 'TAX002', '2024-02-01', NULL)"
    )
    conn.execute(
        "INSERT INTO clients VALUES (3, 'Deleted Corp', 'Bob', 'bob@del.com', 'inactive', 'accounting', 'paid', 'TAX003', '2024-03-01', '2024-06-01')"
    )
    conn.execute(
        "INSERT INTO clients VALUES (4, 'Inactive Inc', 'Ivy', 'ivy@in.com', 'inactive', 'tax', 'pending', 'TAX004', '2024-04-01', NULL)"
    )
    conn.execute("INSERT INTO tasks VALUES (1, 1, 'File VAT', 'pending', 'tax', '2026-10-01', NULL)")
    conn.execute("INSERT INTO tasks VALUES (2, 1, 'Submit report', 'completed', 'reporting', '2026-09-15', NULL)")
    conn.execute("INSERT INTO tasks VALUES (3, 2, 'Audit prep', 'pending', 'audit', '2026-11-01', NULL)")
    conn.execute(
        "INSERT INTO pipeline_items VALUES (1, 1, 'Work Permit', 8, '2026-09-01', NULL, '2026-01-01', '2026-09-01', NULL)"
    )
    conn.execute(
        "INSERT INTO pipeline_items VALUES (2, 2, 'Visa', 4, '2026-09-01', NULL, '2026-01-01', '2026-09-01', NULL)"
    )
    conn.execute(
        "INSERT INTO pipeline_items VALUES (3, 1, 'Done Svc', 9, '2026-09-01', NULL, '2026-01-01', '2026-09-01', NULL)"
    )
    conn.execute(
        "INSERT INTO pipeline_items VALUES (4, 4, 'Inactive Svc', 2, '2026-09-01', NULL, '2026-01-01', '2026-09-01', NULL)"
    )
    _svc = "Monthly Tax Filing Service"
    # Overdue unpaid service-type (payment_date in the past)
    conn.execute(
        f"INSERT INTO documents VALUES (1, 1, '{_svc}', '2026-09-30', '2020-01-01', 5000.0, 0, 'inv001.pdf', NULL)"
    )
    # Paid — not overdue
    conn.execute(
        f"INSERT INTO documents VALUES (2, 1, '{_svc}', '2026-12-31', '2020-02-01', 1200.0, 1, 'rec001.pdf', NULL)"
    )
    # Future payment_date — not overdue
    conn.execute(
        f"INSERT INTO documents VALUES (3, 2, '{_svc}', '2026-08-15', '2099-01-01', 3000.0, 0, 'inv002.pdf', NULL)"
    )
    # Unpaid past payment but inactive client — excluded
    conn.execute(
        f"INSERT INTO documents VALUES (4, 4, '{_svc}', '2026-01-01', '2020-03-01', 100.0, 0, 'inv003.pdf', NULL)"
    )
    # NULL paid treated as unpaid overdue (service type)
    conn.execute(
        f"INSERT INTO documents VALUES (5, 2, '{_svc}', '2026-01-01', '2020-04-01', 200.0, NULL, 'inv004.pdf', NULL)"
    )
    # Overdue unpaid but non-service document_type — excluded by service-type filter
    conn.execute(
        "INSERT INTO documents VALUES (6, 1, 'Other Document', '2026-01-01', '2020-05-01', 50.0, 0, 'other.pdf', NULL)"
    )
    conn.commit()

    class DBWrapper:
        def __init__(self, conn):
            self._conn = conn

        def read_connection(self):
            from contextlib import contextmanager

            @contextmanager
            def _ctx():
                yield self._conn

            return _ctx()

        def list_service_types(self):
            return ["Monthly Tax Filing Service", "Company Annual Accounting Service"]

    yield DBWrapper(conn)
    conn.close()


@pytest.fixture
def skyagent_db(in_memory_db):
    return SkyAgentDB(in_memory_db)


class TestSafeFetchAll:
    def test_rejects_non_select(self, skyagent_db):
        with pytest.raises(DatabaseReadOnlyError, match="Only SELECT"):
            skyagent_db._safe_fetch_all("INSERT INTO clients (name) VALUES (?)", ("test",))

    def test_rejects_multiple_statements(self, skyagent_db):
        with pytest.raises((ValueError, DatabaseReadOnlyError)):
            skyagent_db._safe_fetch_all("SELECT * FROM clients; DROP TABLE clients")

    def test_allows_semicolon_inside_quotes(self, skyagent_db):
        result = skyagent_db._safe_fetch_all("SELECT * FROM clients WHERE name = 'test; drop'")
        assert isinstance(result, list)

    def test_handles_case_insensitive_select(self, skyagent_db):
        result = skyagent_db._safe_fetch_all("select * FROM clients")
        assert isinstance(result, list)

    def test_handles_leading_whitespace(self, skyagent_db):
        result = skyagent_db._safe_fetch_all("   SELECT * FROM clients")
        assert isinstance(result, list)

    def test_returns_dicts(self, skyagent_db):
        result = skyagent_db._safe_fetch_all("SELECT id, name FROM clients WHERE id = 1")
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "ABC Corp"


class TestSafeFetchOne:
    def test_returns_first_row(self, skyagent_db):
        result = skyagent_db._safe_fetch_one("SELECT * FROM clients WHERE id = 1")
        assert result is not None
        assert result["id"] == 1

    def test_returns_none_when_empty(self, skyagent_db):
        result = skyagent_db._safe_fetch_one("SELECT * FROM clients WHERE id = 999")
        assert result is None

    def test_does_not_append_limit_if_present(self, skyagent_db):
        result = skyagent_db._safe_fetch_one("SELECT * FROM clients LIMIT 1")
        assert result is not None


class TestSearchClients:
    def test_finds_by_name(self, skyagent_db):
        results = skyagent_db.search_clients("ABC")
        assert len(results) == 1
        assert results[0]["name"] == "ABC Corp"

    def test_finds_by_contact(self, skyagent_db):
        results = skyagent_db.search_clients("Jane")
        assert len(results) == 1
        assert results[0]["name"] == "XYZ Ltd"

    def test_excludes_deleted(self, skyagent_db):
        results = skyagent_db.search_clients("Deleted")
        assert len(results) == 0

    def test_respects_limit(self, skyagent_db):
        results = skyagent_db.search_clients("Corp", limit=1)
        assert len(results) == 1

    def test_redacts_email(self, skyagent_db):
        results = skyagent_db.search_clients("ABC")
        assert results[0]["email"] == "***REDACTED***"


class TestGetClientTasks:
    def test_returns_tasks_for_client(self, skyagent_db):
        results = skyagent_db.get_client_tasks(1)
        assert len(results) == 2
        titles = {r["title"] for r in results}
        assert "File VAT" in titles
        assert "Submit report" in titles

    def test_excludes_other_clients(self, skyagent_db):
        results = skyagent_db.get_client_tasks(2)
        assert len(results) == 1
        assert results[0]["title"] == "Audit prep"

    def test_excludes_deleted(self, skyagent_db):
        all_results = skyagent_db.get_client_tasks(1)
        assert len(all_results) == 2
        titles = {r["title"] for r in all_results}
        assert "Deleted Task" not in titles


class TestGetDocumentsByClient:
    def test_returns_documents(self, skyagent_db):
        results = skyagent_db.get_documents_by_client(1)
        assert len(results) == 3

    def test_excludes_other_clients(self, skyagent_db):
        results = skyagent_db.get_documents_by_client(2)
        assert len(results) == 2


class TestGetPendingTasks:
    def test_returns_incomplete_pipeline(self, skyagent_db):
        results = skyagent_db.get_pending_tasks()
        assert len(results) == 2
        assert all("step_label" in r for r in results)
        assert all(int(r["step"]) < 9 for r in results)

    def test_includes_client_and_service(self, skyagent_db):
        results = skyagent_db.get_pending_tasks()
        names = {r["client_name"] for r in results}
        services = {r["service"] for r in results}
        assert "ABC Corp" in names
        assert "XYZ Ltd" in names
        assert "Work Permit" in services
        assert "Visa" in services


class TestGetOverdueDocuments:
    def test_payment_date_semantics(self, skyagent_db):
        results = skyagent_db.get_overdue_documents()
        ids = {r["id"] for r in results}
        assert 1 in ids  # unpaid past payment_date (service type)
        assert 5 in ids  # NULL paid coalesced to unpaid
        assert 2 not in ids  # paid
        assert 3 not in ids  # future payment_date
        assert 4 not in ids  # inactive client
        assert 6 not in ids  # non-service document_type
        for r in results:
            assert "payment_date" in r
            assert r["client_name"] is not None

    def test_includes_service_type_overdue(self, skyagent_db):
        results = skyagent_db.get_overdue_documents()
        by_id = {r["id"]: r for r in results}
        assert 1 in by_id
        assert by_id[1]["document_type"] == "Monthly Tax Filing Service"

    def test_excludes_non_service_overdue(self, skyagent_db):
        results = skyagent_db.get_overdue_documents()
        assert all(r["document_type"] != "Other Document" for r in results)
        assert 6 not in {r["id"] for r in results}

    def test_empty_service_types_returns_empty(self, in_memory_db, skyagent_db):
        in_memory_db.list_service_types = lambda: []
        assert skyagent_db.get_overdue_documents() == []


class TestGetClientSummary:
    def test_returns_client_redacted(self, skyagent_db):
        result = skyagent_db.get_client_summary(1)
        assert result is not None
        assert result["name"] == "ABC Corp"
        assert result["email"] == "***REDACTED***"
        assert result["tax_id"] == "***REDACTED***"

    def test_returns_none_for_missing(self, skyagent_db):
        result = skyagent_db.get_client_summary(999)
        assert result is None


class TestRedactFields:
    def test_redacts_when_enabled(self, skyagent_db):
        rows = [{"email": "test@example.com", "name": "Test"}]
        result = skyagent_db._redact_fields(rows, {"email"})
        assert result[0]["email"] == "***REDACTED***"
        assert result[0]["name"] == "Test"

    def test_no_redact_when_disabled(self, skyagent_db):
        skyagent_db._decrypt = True
        rows = [{"email": "test@example.com"}]
        result = skyagent_db._redact_fields(rows, {"email"})
        assert result[0]["email"] == "test@example.com"
