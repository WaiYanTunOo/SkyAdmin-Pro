"""Versioned database migrations."""

from __future__ import annotations

from skyadmin_pro.db.migrations import (
    m001_legacy_schema,
    m002_backfill_sync_global_ids,
    m003_secret_fields,
    m004_legacy_vault,
    m005_ird_to_client_credentials,
    m006_pricing_matrix_services,
    m007_client_credentials_login_id,
    m008_perf_query_indexes,
    m009_client_groups,
    m010_fts_rebuild,
    m011_client_groups_sync,
    m012_sync_hlc,
)
from skyadmin_pro.db.migrations.runner import register_migrations, run_pending_migrations

register_migrations(
    [
        (m001_legacy_schema.VERSION, m001_legacy_schema.NAME, m001_legacy_schema.upgrade),
        (
            m002_backfill_sync_global_ids.VERSION,
            m002_backfill_sync_global_ids.NAME,
            m002_backfill_sync_global_ids.upgrade,
        ),
        (m003_secret_fields.VERSION, m003_secret_fields.NAME, m003_secret_fields.upgrade),
        (m004_legacy_vault.VERSION, m004_legacy_vault.NAME, m004_legacy_vault.upgrade),
        (
            m005_ird_to_client_credentials.VERSION,
            m005_ird_to_client_credentials.NAME,
            m005_ird_to_client_credentials.upgrade,
        ),
        (m006_pricing_matrix_services.VERSION, m006_pricing_matrix_services.NAME, m006_pricing_matrix_services.upgrade),
        (
            m007_client_credentials_login_id.VERSION,
            m007_client_credentials_login_id.NAME,
            m007_client_credentials_login_id.upgrade,
        ),
        (m008_perf_query_indexes.VERSION, m008_perf_query_indexes.NAME, m008_perf_query_indexes.upgrade),
        (m009_client_groups.VERSION, m009_client_groups.NAME, m009_client_groups.upgrade),
        (m010_fts_rebuild.VERSION, m010_fts_rebuild.NAME, m010_fts_rebuild.upgrade),
        (
            m011_client_groups_sync.VERSION,
            m011_client_groups_sync.NAME,
            m011_client_groups_sync.upgrade,
        ),
        (
            m012_sync_hlc.VERSION,
            m012_sync_hlc.NAME,
            m012_sync_hlc.upgrade,
        ),
    ]
)

__all__ = ["run_pending_migrations"]
