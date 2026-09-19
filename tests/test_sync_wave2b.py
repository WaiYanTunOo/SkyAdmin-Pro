"""Wave 2b — expand SYNC_TABLES for web surface (pipeline/suppliers/courier/tax)."""

from __future__ import annotations

from skyadmin_pro.services.sync_schema import (
    CLIENT_FK_TABLES,
    FK_CLIENT_COLUMN,
    FK_SUPPLIER_COLUMN,
    FK_TASK_COLUMN,
    SUPPLIER_FK_TABLES,
    SYNC_ALLOWED_COLUMNS,
    SYNC_EXCLUDED_COLUMNS,
    SYNC_SCHEMA_VERSION,
    SYNC_TABLES,
    TASK_FK_TABLES,
)

WAVE2B = (
    "pipeline_items",
    "suppliers",
    "supplier_payments",
    "supplier_services",
    "courier_logs",
    "client_months",
    "renewal_items",
    "tax_cycle_log",
    "recurring_tasks",
)


def test_wave2b_tables_in_sync_manifest():
    assert SYNC_SCHEMA_VERSION == 7
    for table in WAVE2B:
        assert table in SYNC_TABLES
        assert table in SYNC_ALLOWED_COLUMNS
        assert table in SYNC_EXCLUDED_COLUMNS


def test_wave2b_fk_allowlists():
    assert "pipeline_items" in CLIENT_FK_TABLES
    assert "courier_logs" in CLIENT_FK_TABLES
    assert "courier_logs" in TASK_FK_TABLES
    assert "supplier_payments" in CLIENT_FK_TABLES
    assert "supplier_payments" in SUPPLIER_FK_TABLES
    assert "supplier_services" in SUPPLIER_FK_TABLES
    assert FK_CLIENT_COLUMN in SYNC_ALLOWED_COLUMNS["pipeline_items"]
    assert FK_SUPPLIER_COLUMN in SYNC_ALLOWED_COLUMNS["supplier_payments"]
    assert FK_TASK_COLUMN in SYNC_ALLOWED_COLUMNS["courier_logs"]
    assert "client_id" in SYNC_EXCLUDED_COLUMNS["courier_logs"]
    assert "task_id" in SYNC_EXCLUDED_COLUMNS["courier_logs"]
    assert "supplier_id" in SYNC_EXCLUDED_COLUMNS["supplier_services"]


def test_settings_and_pricing_not_synced():
    assert "settings" not in SYNC_TABLES
    assert "pricing_matrix" not in SYNC_TABLES
    assert "snippet_versions" not in SYNC_TABLES
