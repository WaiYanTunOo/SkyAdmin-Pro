# Database Layer — Feature Detail

## Purpose
SQLite facade, 12 domain mixins, 21 versioned migrations, FTS5, 40+ indexes, single-connection dashboard snapshot (pooling deferred).

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| Facade | `skyadmin_pro/db/database.py` | `Database` (composes 12 mixins) |
| Core | `skyadmin_pro/db/core/` | `_fetch_all()`, `_fetch_one()`, connection helpers, `bundle_queries()` |
| Schema | `skyadmin_pro/db/schema/` | 18 tables, 40+ indexes |
| SQL helpers | `skyadmin_pro/db/sql_helpers.py` | Query builder utilities |
| Cipher | `skyadmin_pro/db/cipher.py` | Database encryption layer |

### Domain Mixins

| Mixin | File | Tables |
|-------|------|--------|
| Core | `db/core/` | connection helpers, `bundle_queries()`, FTS, migrations, backup |
| Clients | `db/clients.py` | `clients`, `clients_fts`, `client_groups` |
| Tasks | `db/tasks.py` | `tasks` |
| Suppliers | `db/suppliers.py` | `suppliers`, `supplier_payments`, `supplier_services` |
| Courier | `db/courier.py` | `courier_logs` |
| Pipeline | `db/pipeline/` | `pipeline_items`, `renewal_items`, `checklist_templates`, `service_renewals` |
| Financial | `db/financial/` | `financial_documents`, `pricing_matrix` |
| Office | `db/office/` | `office_contacts`, `office_credentials`, `notebook_entries` |
| Pricing | `db/pricing/` | `pricing_matrix` |
| Settings | `db/settings.py` | `settings` |
| Tax | `db/tax/` | `client_months`, `tax_cycle_log`, `dashboard_snapshot()` |
| Appointments | `db/appointments/` | `appointments` |

### Migrations

| Migration | File | Purpose |
|-----------|------|---------|
| m001 | `db/migrations/m001_legacy_schema/` | Legacy schema + FTS5 backfill |
| m002 | `db/migrations/m002_backfill_sync_global_ids.py` | Backfill global IDs |
| m003 | `db/migrations/m003_secret_fields.py` | Secret fields encryption |
| m004 | `db/migrations/m004_legacy_vault.py` | Legacy vault migration |
| m005 | `db/migrations/m005_ird_to_client_credentials.py` | IRD → client credentials |
| m006 | `db/migrations/m006_pricing_matrix_services.py` | Pricing matrix services |
| m007 | `db/migrations/m007_client_credentials_login_id.py` | Client credentials login ID |
| m008 | `db/migrations/m008_perf_query_indexes.py` | Composite overdue/ongoing indexes |
| m009 | `db/migrations/m009_client_groups.py` | Client groups table |
| m010 | `db/migrations/m010_fts_rebuild.py` | FTS5 rebuild |
| m011 | `db/migrations/m011_client_groups_sync.py` | Client groups sync columns |
| m012 | `db/migrations/m012_sync_hlc.py` | HLC sync ordering |
| m013 | `db/migrations/m013_task_dependencies.py` | Task dependencies |
| m014 | `db/migrations/m014_recurring_tasks.py` | Recurring tasks |
| m015 | `db/migrations/m015_pnd_monthly_annual.py` | PND monthly/annual |
| m016 | `db/migrations/m016_credentials_sync.py` | Credentials sync |
| m017 | `db/migrations/m017_documents_sync.py` | Documents sync |
| m018 | `db/migrations/m018_wave2b_sync.py` | Wave 2B sync columns |
| m019 | `db/migrations/m019_sync_conflict_actors.py` | Conflict actor tracking |
| m020 | `db/migrations/m020_appointments.py` | Appointments |
| m021 | `db/migrations/m021_drop_redundant_indexes.py` | Drop redundant `idx_clients_name` |
| Runner | `db/migrations/runner.py` | `register_migrations`, `run_pending_migrations` |

## Architecture Decisions
- **Facade pattern**: `Database` composes 12 domain mixins — clean separation.
- **Versioned migrations**: `schema_migrations` table tracks applied migrations (21 live, m001–m021).
- **FTS5**: virtual table `clients_fts` with triggers; `search_clients()` falls back to LIKE.
- **40+ indexes**: audited 2026-09 (T008); redundant `idx_clients_name` dropped via migration 021.
- **Single-connection snapshot**: `dashboard_snapshot()` runs inside `bundle_queries()` — 1 pinned connection / ≤40 statements (T001).
- **Connection**: new per query outside bundles (acceptable until measured pain; pool audit done, pooling deferred).

## Tests

| File | Covers |
|------|--------|
| `tests/test_db_migrations.py` | Migration runner, version tracking |
| `tests/test_db_mixins.py` | Domain mixin CRUD |
| `tests/test_db_pricing.py` | Pricing matrix |
| `tests/test_db_settings.py` | Settings get/set |
| `tests/test_db_cipher.py` | Cipher layer |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 7.1 | Versioned DB migrations | ✅ Landed |
| Phase 10.1 | FTS5 client search | ✅ Landed |
| Phase 10.2 | Treeview incremental update | ✅ Landed |
| Phase 10.4 | Composite indexes + migration 008 | ✅ Landed |
| Phase 10.5 | Perf regression tests | ✅ Landed |
| T008 | Index redundancy audit (drop `idx_clients_name`, m021) | ✅ Landed |
| T001 | Dashboard snapshot single connection | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| New SQLite connection per query (no pooling) | `db/core/` | P0 (deferred — audited) |
| `dashboard_snapshot()` opens 12+ connections | `db/tax/` | ✅ Fixed — single `bundle_queries()` connection (T001) |
| Monolithic `_migrate()` | `db/migrations/` | ✅ Fixed — versioned migrations (P1.3) |
| `_fetch_all`/`_fetch_one` in wrong mixin | `db/clients.py` | ✅ Fixed |
| 40+ indexes — rest of the audit | `db/schema/` | ✅ Audited (T008) — `idx_clients_name` dropped |
