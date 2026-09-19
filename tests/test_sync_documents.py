"""Wave 2a — documents / financial_documents sync schema."""

from __future__ import annotations

from skyadmin_pro.services.sync_schema import (
    FK_CLIENT_COLUMN,
    SYNC_ALLOWED_COLUMNS,
    SYNC_EXCLUDED_COLUMNS,
    SYNC_SCHEMA_VERSION,
    SYNC_TABLES,
)


def test_documents_tables_in_sync_manifest():
    assert SYNC_SCHEMA_VERSION == 7
    assert "documents" in SYNC_TABLES
    assert "financial_documents" in SYNC_TABLES


def test_documents_allowlists_include_drive_file_id():
    for table in ("documents", "financial_documents"):
        allowed = SYNC_ALLOWED_COLUMNS[table]
        assert "drive_file_id" in allowed
        assert "drive_parent_path" in allowed
        assert "content_hash" in allowed
        assert FK_CLIENT_COLUMN in allowed
        assert "client_id" not in allowed
        assert "client_id" in SYNC_EXCLUDED_COLUMNS[table]
