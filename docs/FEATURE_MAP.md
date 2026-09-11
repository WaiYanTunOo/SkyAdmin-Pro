# SkyAdmin Pro — Feature Map

Master reference: every feature's code files, tests, docs, and fix locations.

**Version:** `0.3.3` · **Updated:** 2026-09-11

---

## Quick Navigation

| # | Feature | Detail File | Roadmap Phase |
|---|---------|-------------|---------------|
| F1 | [Dashboard](#f1-dashboard) | [features/dashboard.md](features/dashboard.md) | Phase 7.2, 9.3 |
| F2 | [Database & Tasks](#f2-database--tasks) | [features/database_tasks.md](features/database_tasks.md) | Phase 9.1 |
| F3 | [Company Details](#f3-company-details) | [features/company_details.md](features/company_details.md) | Phase 9B |
| F4 | [Document Hub](#f4-document-hub) | [features/document_hub.md](features/document_hub.md) | Phase 9.2 |
| F5 | [Office Hub](#f5-office-hub) | [features/office_hub.md](features/office_hub.md) | Phase 9.4 |
| F6 | [Settings](#f6-settings) | [features/settings.md](features/settings.md) | Phase 9B |
| F7 | [UI Widgets](#f7-ui-widgets) | [features/ui_widgets.md](features/ui_widgets.md) | Phase 9C |
| F8 | [Licensing & Activation](#f8-licensing--activation) | [features/licensing.md](features/licensing.md) | Phase 8 |
| F9 | [Data Sync](#f9-data-sync) | [features/data_sync.md](features/data_sync.md) | Phase 8, Wave C |
| F10 | [Export & Reports](#f10-export--reports) | [features/export_reports.md](features/export_reports.md) | Phase 8.4 |
| F11 | [Backup & Restore](#f11-backup--restore) | [features/backup_restore.md](features/backup_restore.md) | Phase 7 |
| F12 | [Security & Crypto](#f12-security--crypto) | [features/security_crypto.md](features/security_crypto.md) | Phase 8, S1 |
| F13 | [i18n & Translation](#f13-i18n--translation) | [features/i18n.md](features/i18n.md) | — |
| F14 | [Database Layer](#f14-database-layer) | [features/database_layer.md](features/database_layer.md) | Phase 7.1, 10 |
| F15 | [Config](#f15-config) | [features/config.md](features/config.md) | — |
| F16 | [Cloudflare Worker](#f16-cloudflare-worker) | [features/worker_api.md](features/worker_api.md) | Phase 8, S1 |
| F17 | [CI/CD & Packaging](#f17-cicd--packaging) | [features/cicd_packaging.md](features/cicd_packaging.md) | Phase 11 |
| F18 | [Utilities](#f18-utilities) | [features/utilities.md](features/utilities.md) | — |
| F19 | [Other Views](#f19-other-views) | [features/other_views.md](features/other_views.md) | — |

---

## F1. Dashboard

Stat cards, progressive detail trees, fingerprinting, EOD report.

| Layer | File |
|-------|------|
| UI | `skyadmin_pro/ui/views/dashboard.py` |
| DB query | `skyadmin_pro/db/tax.py` |
| Tracking | `skyadmin_pro/services/tracking.py` |
| Snippets | `skyadmin_pro/services/snippets.py` |
| Workflow | `skyadmin_pro/services/workflow.py` |
| Config | `skyadmin_pro/config/services.py` |
| Tests | `tests/test_dashboard_layout.py`, `test_dashboard_paint.py`, `test_dashboard_refresh.py` |
| Doc | `docs/ROADMAP.md` Phase 7.2, 9.3 |
| **Fix** | `dashboard.py:build()` first paint; `db/tax.py:dashboard_snapshot()` ≤3 SQL |

→ [Full detail](features/dashboard.md)

---

## F2. Database & Tasks

Clients, tasks, suppliers, pipeline, renewal, courier — active-tab-only refresh.

| Layer | File |
|-------|------|
| Tab container | `skyadmin_pro/ui/views/database_tasks/view.py` |
| Constants | `skyadmin_pro/ui/views/database_tasks/constants.py` |
| Clients | `skyadmin_pro/ui/views/database_tasks/clients_panel.py` |
| Tasks | `skyadmin_pro/ui/views/database_tasks/task_panel.py` |
| Suppliers | `skyadmin_pro/ui/views/database_tasks/suppliers_panel.py` |
| Pipeline | `skyadmin_pro/ui/views/database_tasks/pipeline_panel.py` |
| Renewal | `skyadmin_pro/ui/views/database_tasks/renewal_panel.py` |
| Courier | `skyadmin_pro/ui/views/database_tasks/courier_panel.py` |
| Suppliers sub | `skyadmin_pro/ui/views/database_tasks/suppliers/panel.py`, `directory_tab.py`, `payments_tab.py`, `services_tab.py` |
| DB mixins | `skyadmin_pro/db/clients.py`, `tasks.py`, `suppliers.py`, `courier.py`, `pipeline.py`, `financial.py` |
| Tests | `tests/test_database_tasks_refresh.py`, `test_clients_bulk_ops.py`, `test_supplier_ap.py` |
| Doc | `docs/ROADMAP.md` Phase 9.1 |

→ [Full detail](features/database_tasks.md)

---

## F3. Company Details

Per-company services, tax, VO/CSH, documents — 7-mixin lazy sub-tabs.

| Layer | File |
|-------|------|
| Panel | `skyadmin_pro/ui/views/company_details/panel.py` |
| Constants | `skyadmin_pro/ui/views/company_details/constants.py` |
| General | `skyadmin_pro/ui/views/company_details/general_tab.py` |
| Accounting | `skyadmin_pro/ui/views/company_details/accounting_setup_tab.py` |
| Tax IDs | `skyadmin_pro/ui/views/company_details/tax_ids_tab.py` |
| Filing | `skyadmin_pro/ui/views/company_details/filing_tab.py` |
| VO/CSH Setup | `skyadmin_pro/ui/views/company_details/vo_csh_setup_tab.py` |
| VO & CSH | `skyadmin_pro/ui/views/company_details/vo_csh_tab.py` |
| Financial Docs | `skyadmin_pro/ui/views/company_details/financial_docs_tab.py` |
| Rollout | `skyadmin_pro/services/tax_ids_rollout.py`, `vo_csh_rollout.py` |
| Tests | `tests/test_company_details_refresh.py`, `test_tax_ids_rollout.py`, `test_vo_csh_rollout.py` |
| **Fix** | `panel.py:57–74` 7-mixin MRO; `panel.py:244–302` redundant refresh |

→ [Full detail](features/company_details.md)

---

## F4. Document Hub

Folder/document workflows, 6 tool panels, poll pauses when hidden.

| Layer | File |
|-------|------|
| View | `skyadmin_pro/ui/views/document_hub/view.py` |
| Agent Bundle | `skyadmin_pro/ui/views/document_hub/agent_bundle.py` |
| Archive | `skyadmin_pro/ui/views/document_hub/archive.py` |
| Financial | `skyadmin_pro/ui/views/document_hub/financial.py` |
| Image/PDF | `skyadmin_pro/ui/views/document_hub/image_pdf.py` |
| Portal | `skyadmin_pro/ui/views/document_hub/portal.py` |
| Renamer | `skyadmin_pro/ui/views/document_hub/renamer.py` |
| Helpers | `skyadmin_pro/ui/views/document_hub/helpers.py` |
| Tests | `tests/test_document_hub_polling.py` |

→ [Full detail](features/document_hub.md)

---

## F5. Office Hub

Contacts, vault, notebook, setup — search debounce 300ms.

| Layer | File |
|-------|------|
| View | `skyadmin_pro/ui/views/office_hub/view.py` |
| Contacts | `skyadmin_pro/ui/views/office_hub/contacts_tab.py` |
| Vault | `skyadmin_pro/ui/views/office_hub/vault_tab.py` |
| Notebook | `skyadmin_pro/ui/views/office_hub/notebook_tab.py` |
| Setup | `skyadmin_pro/ui/views/office_hub/setup_tab.py` |
| Rollout | `skyadmin_pro/services/office_hub_rollout.py` |
| Tests | `tests/test_office_hub.py`, `test_office_hub_rollout.py` |

→ [Full detail](features/office_hub.md)

---

## F6. Settings

Appearance, license, business defaults, backup, pricing, checklist.

| Layer | File |
|-------|------|
| View | `skyadmin_pro/ui/views/settings/view.py` |
| License | `skyadmin_pro/ui/views/settings/license_mixin.py` |
| Pricing | `skyadmin_pro/ui/views/settings/pricing_mixin.py` |
| Backup | `skyadmin_pro/ui/views/settings/backup_mixin.py` |
| Checklist | `skyadmin_pro/ui/views/settings/checklist_mixin.py` |
| Workspace | `skyadmin_pro/ui/views/settings/workspace_mixin.py` |
| Sync conflicts | `skyadmin_pro/ui/views/settings/sync_conflicts_dialog.py` |
| Tests | `tests/test_settings_lazy_tabs.py` |

→ [Full detail](features/settings.md)

---

## F7. UI Widgets

DatePickerField, ThemedTreeview, CanvasScrollFrame, theme, DPI, debounce.

| Layer | File |
|-------|------|
| Widgets | `skyadmin_pro/ui/widgets.py` |
| Treeview | `skyadmin_pro/ui/treeview.py` |
| Canvas scroll | `skyadmin_pro/ui/canvas_scroll.py` |
| Theme | `skyadmin_pro/ui/theme.py` |
| High-DPI | `skyadmin_pro/ui/display.py` |
| Debounce | `skyadmin_pro/ui/debounce.py` |
| DnD | `skyadmin_pro/ui/dnd.py` |
| Combobox | `skyadmin_pro/ui/combo_utils.py` |
| Async UI | `skyadmin_pro/ui/async_ui.py` |
| Tests | `tests/test_date_picker.py`, `test_canvas_scroll.py`, `test_treeview_*.py`, `test_form_widgets.py`, `test_display_scaling.py` |
| **Fix** | `widgets.py:635–638` root binds; `widgets.py:798–799` `-topmost` flicker |

→ [Full detail](features/ui_widgets.md)

---

## F8. Licensing & Activation

Ed25519 signed keys, machine binding, activation claim, ban/revoke.

| Layer | File |
|-------|------|
| Package | `skyadmin_pro/services/license/__init__.py` |
| Machine ID | `skyadmin_pro/services/license/machine.py` |
| Online | `skyadmin_pro/services/license/online.py` |
| Verify | `skyadmin_pro/services/license/verify.py` |
| Constants | `skyadmin_pro/services/license/_constants.py` |
| Authoring | `skyadmin_pro/services/license_authoring.py` |
| Crypto | `skyadmin_pro/services/license_crypto.py` |
| Public | `skyadmin_pro/services/license_public.py` |
| Activation UI | `skyadmin_pro/ui/activation.py` |
| Setup rollout | `skyadmin_pro/ui/setup_rollout.py` |
| Integrity | `main.py:390–435` CRC32 tamper detection |
| Periodic | `main.py:520–572` 5-min re-verify |
| Worker routes | `skyadmin-worker/src/routes/generate.ts`, `claim.ts`, `control.ts`, `revoke.ts`, `ban.ts`, `used.ts`, `records.ts` |
| Worker core | `skyadmin-worker/src/verification.ts`, `signing.ts`, `license_policy.ts`, `license_status.ts`, `packages.ts` |
| Tests | `tests/test_license_ed25519.py`, `test_license_security.py`, `test_activation_dialog.py` |
| Worker tests | `auth.test.ts`, `signing.test.ts`, `verification.test.ts`, `license_policy.test.ts`, `license_status.test.ts`, `packages.test.ts`, `claim.test.ts`, `control.test.ts`, `handlers.test.ts`, `admin.test.ts`, `lifecycle.test.ts` |
| **Fix** | `verify.py` monolith; `generate.ts:25–27` dynamic import |

→ [Full detail](features/licensing.md)

---

## F9. Data Sync

Pull/push, LWW conflicts, encrypted credentials, HLC ordering.

| Layer | File |
|-------|------|
| Desktop sync | `skyadmin_pro/services/data_sync.py` |
| Sync schema | `skyadmin_pro/services/sync_schema.py` |
| Sync HLC | `skyadmin_pro/services/sync_hlc.py` |
| Worker sync | `skyadmin-worker/src/routes/sync.ts` |
| Worker auth | `skyadmin-worker/src/sync_auth.ts` |
| Worker eligibility | `skyadmin-worker/src/sync_eligibility.ts` |
| Worker push | `skyadmin-worker/src/sync_push.ts` |
| Worker devices | `skyadmin-worker/src/sync_devices_schema.ts` |
| Worker schema | `skyadmin-worker/src/sync_schema.ts` |
| Tests | `tests/test_data_sync.py`, `test_sync_hlc.py`, `sync.test.ts`, `sync_push.test.ts` |
| **Fix** | `data_sync.py:86–91` plaintext fallback; `sync.ts:132` LIMIT interpolation |

→ [Full detail](features/data_sync.md)

---

## F10. Export & Reports

Excel export with column redaction, PDF reports, data import.

| Layer | File |
|-------|------|
| Export | `skyadmin_pro/services/export.py` |
| Reports | `skyadmin_pro/services/reports.py` |
| PDF render | `skyadmin_pro/services/pdf_render.py` |
| Import | `skyadmin_pro/services/importer.py` |
| Tests | `tests/test_export_security.py`, `test_export_supplier.py`, `test_export_visible.py`, `test_reports.py`, `test_importer.py` |

→ [Full detail](features/export_reports.md)

---

## F11. Backup & Restore

Manual + auto-backup, encrypted, retention policy.

| Layer | File |
|-------|------|
| Auto backup | `skyadmin_pro/services/auto_backup.py` |
| DB pool | `skyadmin_pro/db/core.py` |
| Settings UI | `skyadmin_pro/ui/views/settings/backup_mixin.py` |
| Tests | `tests/test_auto_backup.py`, `test_restore_backup_pool.py` |

→ [Full detail](features/backup_restore.md)

---

## F12. Security & Crypto

Fernet encryption, HMAC integrity, CORS, CSP, rate limiting, timing-safe.

| Layer | File |
|-------|------|
| Secret fields | `skyadmin_pro/services/secret_fields.py` |
| Vault | `skyadmin_pro/services/vault.py` |
| Crypto | `skyadmin_pro/services/crypto.py` |
| DB cipher | `skyadmin_pro/db/cipher.py` |
| Protect core | `skyadmin_pro/services/_protect_core.py` |
| Secret config | `skyadmin_pro/services/_secret.py` |
| Tests | `tests/test_secret_fields.py`, `test_vault.py`, `test_crypto.py`, `test_db_cipher.py` |
| Worker auth | `skyadmin-worker/src/auth.ts`, `timing_safe.ts` |
| Worker CORS | `skyadmin-worker/src/cors.ts` |
| Worker CSP | `skyadmin-worker/src/csp.ts` |
| Worker rate limit | `skyadmin-worker/src/rate_limit.ts` |
| Worker admin sec | `skyadmin-worker/src/admin_security.ts` |
| Worker tests | `auth.test.ts`, `cors.test.ts`, `rate_limit.test.ts`, `integration_security.test.ts` |
| **Fix** | `_protect_core.py:78` HMAC truncated |

→ [Full detail](features/security_crypto.md)

---

## F13. i18n & Translation

Language switching, translation helpers, snippet packs.

| Layer | File |
|-------|------|
| i18n | `skyadmin_pro/services/i18n.py` |
| Translate | `skyadmin_pro/services/translate.py` |
| Snippets | `skyadmin_pro/services/snippets.py` |
| Tests | `tests/test_i18n.py` |
| **Fix** | `i18n.py:59` thread-unsafe `_current_lang` |

→ [Full detail](features/i18n.md)

---

## F14. Database Layer

SQLite facade, 11 mixins, 12 migrations, FTS5, 40+ indexes.

| Layer | File |
|-------|------|
| Facade | `skyadmin_pro/db/database.py` |
| Core | `skyadmin_pro/db/core.py` |
| Schema | `skyadmin_pro/db/schema.py` |
| SQL helpers | `skyadmin_pro/db/sql_helpers.py` |
| Mixins | `skyadmin_pro/db/clients.py`, `tasks.py`, `suppliers.py`, `courier.py`, `pipeline.py`, `financial.py`, `office.py`, `pricing.py`, `settings.py`, `tax.py` |
| Migrations | `skyadmin_pro/db/migrations/runner.py`, `m001`–`m012` |
| Tests | `tests/test_db_migrations.py`, `test_db_mixins.py`, `test_db_pricing.py`, `test_db_settings.py`, `test_db_cipher.py` |
| **Fix** | `core.py:40–72` no pooling; `core.py:209–395` monolithic `_migrate()` |

→ [Full detail](features/database_layer.md)

---

## F15. Config

Application constants, default settings, UI copy.

| Layer | File |
|-------|------|
| Package | `skyadmin_pro/config/__init__.py` |
| Nav | `skyadmin_pro/config/nav.py` |
| Documents | `skyadmin_pro/config/documents.py` |
| Licensing | `skyadmin_pro/config/licensing.py` |
| Office | `skyadmin_pro/config/office.py` |
| Pricing | `skyadmin_pro/config/pricing.py` |
| Services | `skyadmin_pro/config/services.py` |
| Tasks | `skyadmin_pro/config/tasks.py` |
| Workspace | `skyadmin_pro/config/workspace.py` |
| **Fix** | `__init__.py` 301 lines — split checklist data |

→ [Full detail](features/config.md)

---

## F16. Cloudflare Worker

Hono routes, D1 database, auth, CORS, CSP, admin panel.

| Layer | File |
|-------|------|
| Router | `skyadmin-worker/src/index.ts` |
| DB/Env | `skyadmin-worker/src/db.ts`, `env_secrets.ts` |
| Routes | `routes/generate.ts`, `claim.ts`, `revoke.ts`, `ban.ts`, `used.ts`, `records.ts`, `control.ts`, `sync.ts`, `pricing.ts`, `update.ts`, `purge.ts`, `viewer.ts`, `signing_info.ts` |
| Admin | `routes/admin/handler.ts`, `session.ts`, `pages.ts`, `index.ts` |
| Core | `auth.ts`, `cors.ts`, `csp.ts`, `signing.ts`, `verification.ts`, `rate_limit.ts`, `timing_safe.ts`, `admin_security.ts` |
| Sync core | `sync_auth.ts`, `sync_eligibility.ts`, `sync_push.ts`, `sync_devices_schema.ts`, `sync_schema.ts` |
| License core | `license_policy.ts`, `license_status.ts`, `packages.ts` |
| D1 migrations | `migrations/0001_initial.sql`–`0007_drop_redundant_sync_devices_index.sql` |
| Tests | 17 test files in `src/` |
| **Fix** | `records.ts:24–29` full table scan; `generate.ts:25–27` dynamic import |

→ [Full detail](features/worker_api.md)

---

## F17. CI/CD & Packaging

GitHub Actions, PyInstaller, Inno Setup, code signing.

| Layer | File |
|-------|------|
| CI | `.github/workflows/ci.yml` |
| Release | `.github/workflows/release.yml` |
| Deploy | `.github/workflows/deploy.yml` |
| Release check | `scripts/release_check.py` |
| Publish | `scripts/publish_release.py`, `publish_update.py` |
| Changelog | `scripts/generate_changelog.py` |
| Build | `packaging/build.ps1`, `build.cmd`, `build_native.ps1` |
| Installer | `packaging/build-installer.ps1`, `SkyAdminPro.iss` |
| Signing | `packaging/sign-windows.ps1` |
| macOS | `packaging/build-macos.sh`, `SkyAdminPro-macos.spec` |
| Linux | `packaging/build-linux.sh`, `SkyAdminPro-linux.spec` |
| Docs | `packaging/README.md`, `packaging/SIGNING.md` |

→ [Full detail](features/cicd_packaging.md)

---

## F18. Utilities

File ops, workflow, undo, column state, process jobs, network.

| Layer | File |
|-------|------|
| File ops | `skyadmin_pro/services/file_ops.py` |
| Workflow | `skyadmin_pro/services/workflow.py` |
| Undo | `skyadmin_pro/services/undo_manager.py` |
| Column state | `skyadmin_pro/services/column_state.py` |
| Process jobs | `skyadmin_pro/services/process_jobs.py` |
| Remote pricing | `skyadmin_pro/services/remote_pricing.py` |
| Data hygiene | `skyadmin_pro/services/data_hygiene.py` |
| Tax calendar | `skyadmin_pro/services/tax_calendar.py` |
| Tracking | `skyadmin_pro/services/tracking.py` |
| Net | `skyadmin_pro/services/net.py` |
| Storage | `skyadmin_pro/services/storage_backend.py` |
| Client cmds | `skyadmin_pro/services/client_commands.py` |
| Tests | `tests/test_file_ops.py`, `test_workflow.py`, `test_undo.py`, `test_column_state.py`, `test_process_jobs.py`, `test_remote_pricing.py`, `test_data_hygiene.py`, `test_net.py`, `test_storage_backend.py`, `test_workspace_paths.py` |

→ [Full detail](features/utilities.md)

---

## F19. Other Views

Global search, audit log, export filter, utilities view.

| Layer | File |
|-------|------|
| Global search | `skyadmin_pro/ui/views/global_search.py` |
| Audit log | `skyadmin_pro/ui/views/audit_log.py` |
| Export filter | `skyadmin_pro/ui/views/export_filter_dialog.py` |
| Utilities view | `skyadmin_pro/ui/views/utilities.py` |
| Base view | `skyadmin_pro/ui/views/base.py` |
| Tests | `tests/test_audit_log.py`, `test_phase4_walkthrough.py`, `test_visual_regression.py`, `test_ui_smoke.py` |

→ [Full detail](features/other_views.md)

---

## Pending Fixes (by priority)

| # | Pri | Issue | File:Line | Phase |
|---|-----|-------|-----------|-------|
| 1 | P0 | SQLite connection per query | `db/core.py:40–72` | P1.1 |
| 2 | P0 | Dashboard snapshot 12+ connections | `db/tax.py:158–179` | P1.2 |
| 3 | P0 | 100+ bare `except Exception: pass` | `widgets.py`, `display.py`, `canvas_scroll.py`, `treeview.py`, `main_window.py` | Q1 |
| 4 | P1 | Config monolith 301 lines | `config/__init__.py` | Q2 |
| 5 | P1 | 7-mixin MRO | `company_details/panel.py:57–74` | U8 |
| 6 | P1 | `_fetch_all`/`_fetch_one` wrong mixin | `db/clients.py:329–337` | Q4 |
| 7 | P1 | Thread-unsafe `_current_lang` | `services/i18n.py:59` | S19 |
| 8 | P1 | Worker `recordsHandler` full scan | `routes/records.ts:24–29` | P8 |
| 9 | P1 | HMAC seal truncated 64 bits | `services/_protect_core.py:78` | S18 |
| 10 | P2 | Private `_views` across modules | `panel.py:930–932`, `dashboard.py:1092` | U10 |
| 11 | P2 | String-based tab dispatch | `database_tasks/view.py`, `company_details/panel.py` | U11 |
| 12 | P2 | `__import__()` inline | `treeview.py:130–133`, 9+ files | Q5–Q6 |
| 13 | P2 | Dynamic `import()` hot path | `routes/generate.ts:25–27` | P9 |
| 14 | P2 | License before DB insert | `routes/generate.ts:53–55` | P11 |
| 15 | P2 | Duplicate license constants | `license/_constants.py` vs `machine.py` | Q3 |
| 16 | P3 | Plaintext credential fallback | `services/data_sync.py:86–91` | S15 |
| 17 | P3 | `pyarmor.bug.log` in repo | root | S21 |
| 18 | P3 | Dead `@ts-ignore` | `worker/src/auth.ts:16–19` | S23 |
