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
            amount REAL,
            paid INTEGER,
            file_name TEXT,
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
    conn.execute("INSERT INTO tasks VALUES (1, 1, 'File VAT', 'pending', 'tax', '2026-10-01', NULL)")
    conn.execute("INSERT INTO tasks VALUES (2, 1, 'Submit report', 'completed', 'reporting', '2026-09-15', NULL)")
    conn.execute("INSERT INTO tasks VALUES (3, 2, 'Audit prep', 'pending', 'audit', '2026-11-01', NULL)")
    conn.execute("INSERT INTO documents VALUES (1, 1, 'invoice', '2026-09-30', 5000.0, 0, 'inv001.pdf', NULL)")
    conn.execute("INSERT INTO documents VALUES (2, 1, 'receipt', '2026-12-31', 1200.0, 1, 'rec001.pdf', NULL)")
    conn.execute("INSERT INTO documents VALUES (3, 2, 'invoice', '2026-08-15', 3000.0, 0, 'inv002.pdf', NULL)")
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
        assert len(results) == 2

    def test_excludes_other_clients(self, skyagent_db):
        results = skyagent_db.get_documents_by_client(2)
        assert len(results) == 1


class TestGetPendingTasks:
    def test_returns_only_pending(self, skyagent_db):
        results = skyagent_db.get_pending_tasks()
        assert all(r["status"] == "pending" for r in results)
        assert len(results) == 2

    def test_includes_client_name(self, skyagent_db):
        results = skyagent_db.get_pending_tasks()
        names = {r["client_name"] for r in results}
        assert "ABC Corp" in names
        assert "XYZ Ltd" in names


class TestGetOverdueDocuments:
    def test_returns_unpaid_overdue(self, skyagent_db):
        results = skyagent_db.get_overdue_documents()
        assert len(results) > 0
        for r in results:
            assert r["client_name"] is not None


class TestGetClientSummary:
    def test_returns_client(self, skyagent_db):
        result = skyagent_db.get_client_summary(1)
        assert result is not None
        assert result["name"] == "ABC Corp"
        assert result["tax_id"] == "TAX001"

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
