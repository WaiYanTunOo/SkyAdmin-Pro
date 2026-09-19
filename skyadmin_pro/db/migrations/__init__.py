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
    m013_task_dependencies,
    m014_recurring_tasks,
    m015_pnd_monthly_annual,
    m016_credentials_sync,
    m017_documents_sync,
    m018_wave2b_sync,
    m019_sync_conflict_actors,
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
        (
            m013_task_dependencies.VERSION,
            m013_task_dependencies.NAME,
            m013_task_dependencies.upgrade,
        ),
        (
            m014_recurring_tasks.VERSION,
            m014_recurring_tasks.NAME,
            m014_recurring_tasks.upgrade,
        ),
        (
            m015_pnd_monthly_annual.VERSION,
            m015_pnd_monthly_annual.NAME,
            m015_pnd_monthly_annual.upgrade,
        ),
        (
            m016_credentials_sync.VERSION,
            m016_credentials_sync.NAME,
            m016_credentials_sync.upgrade,
        ),
        (
            m017_documents_sync.VERSION,
            m017_documents_sync.NAME,
            m017_documents_sync.upgrade,
        ),
        (
            m018_wave2b_sync.VERSION,
            m018_wave2b_sync.NAME,
            m018_wave2b_sync.upgrade,
        ),
        (
            m019_sync_conflict_actors.VERSION,
            m019_sync_conflict_actors.NAME,
            m019_sync_conflict_actors.upgrade,
        ),
    ]
)

__all__ = ["run_pending_migrations"]
