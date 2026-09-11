# Database Layer — Feature Detail

## Purpose
SQLite facade, 11 domain mixins, 12 versioned migrations, FTS5, 40+ indexes, connection pooling.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| Facade | `skyadmin_pro/db/database.py` | `Database` (composes 11 mixins) |
| Core | `skyadmin_pro/db/core.py` | `_fetch_all()`, `_fetch_one()`, `_migrate()` |
| Schema | `skyadmin_pro/db/schema.py` | 18 tables, 40+ indexes |
| SQL helpers | `skyadmin_pro/db/sql_helpers.py` | Query builder utilities |
| Cipher | `skyadmin_pro/db/cipher.py` | Database encryption layer |

### Domain Mixins

| Mixin | File | Tables |
|-------|------|--------|
| Clients | `db/clients.py` | `clients`, `clients_fts`, `client_groups` |
| Tasks | `db/tasks.py` | `tasks` |
| Suppliers | `db/suppliers.py` | `suppliers`, `supplier_payments`, `supplier_services` |
| Courier | `db/courier.py` | `courier_logs` |
| Pipeline | `db/pipeline.py` | `pipeline_items`, `renewal_items`, `checklist_templates`, `service_renewals` |
| Financial | `db/financial.py` | `financial_documents`, `pricing_matrix` |
| Office | `db/office.py` | `office_contacts`, `office_credentials`, `notebook_entries` |
| Pricing | `db/pricing.py` | `pricing_matrix` |
| Settings | `db/settings.py` | `settings` |
| Tax | `db/tax.py` | `client_months`, `tax_cycle_log`, `dashboard_snapshot()` |

### Migrations

| Migration | File | Purpose |
|-----------|------|---------|
| m001 | `db/migrations/m001_legacy_schema.py` | Legacy schema + FTS5 backfill |
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
| Runner | `db/migrations/runner.py` | Migration runner |

## Architecture Decisions
- **Facade pattern**: `Database` composes 11 domain mixins — clean separation.
- **Versioned migrations**: `schema_migrations` table tracks applied migrations.
- **FTS5**: virtual table `clients_fts` with triggers; `search_clients()` falls back to LIKE.
- **40+ indexes**: well-targeted; audit deferred until 500+ client threshold.
- **Connection**: new per query (acceptable until measured pain; pooling deferred).

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

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| New SQLite connection per query (no pooling) | `db/core.py:40–72` | P0 |
| `dashboard_snapshot()` opens 12+ connections | `db/tax.py:158–179` | P0 |
| Monolithic `_migrate()` (187 lines) | `db/core.py:209–395` | P1 |
| `_fetch_all`/`_fetch_one` in wrong mixin | `db/clients.py:329–337` | P1 |
| 40+ indexes — review for redundancy at 500+ clients | `db/schema.py` | P3 |
