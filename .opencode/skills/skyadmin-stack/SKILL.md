---
name: skyadmin-stack
description: General SkyAdmin Pro project knowledge. Use when working on any part of the codebase to understand the full stack architecture, conventions, and constraints.
---

# SkyAdmin Pro — Stack Knowledge

## Technology Stack

| Layer | Technology |
|-------|------------|
| Desktop UI | Python 3 + CustomTkinter |
| Database | SQLite (`skyadmin_pro/db/`) |
| Backend API | TypeScript Cloudflare Worker (`skyadmin-worker/`) |
| Packaging | PyInstaller (Windows-focused) |

**Not in scope:** Kotlin/Swift/Android/iOS UI. UI bugs are CustomTkinter layout/performance issues, not missing native mobile code.

## Repository Structure

```
main.py                              # Entry point: license gate, single-instance lock
skyadmin_pro/                        # Python desktop app package
  config/                            # Constants: nav, workspace, office, licensing, pricing, services, tasks, documents
  db/                                # SQLite layer (15 .py)
    database.py                      # Database facade — composes 11 mixins
    core.py                          # Connection pooling, _fetch_all/_fetch_one
    schema.py                        # Table DDL (40+ indexes)
    mixins: clients, courier, financial, office, pipeline, pricing, settings, suppliers, tasks, tax
    migrations/                      # m001–m010 versioned migrations + runner
  services/                          # Business logic (32 .py)
    license/                         # Sub-package: machine.py, online.py, verify.py, _constants.py
    crypto.py, i18n.py, export.py, importer.py, workflow.py
    data_sync.py, data_hygiene.py, secret_fields.py, vault.py, storage_backend.py
    reports.py, translate.py, undo_manager.py, auto_backup.py, file_ops.py
  ui/                                # CustomTkinter UI (13 top-level + 52 views .py)
    main_window.py                   # Sidebar nav + view swapping
    widgets.py                       # Shared widgets incl. DatePickerField
    theme.py, display.py, canvas_scroll.py, combo_utils.py, debounce.py, dnd.py
    views/
      dashboard.py
      database_tasks/                # view.py + panels (clients, suppliers, courier, pipeline, renewal, task)
      document_hub/                  # view.py + tools (agent_bundle, archive, financial, portal, renamer, image_pdf)
      company_details/               # panel.py + tabs (general, accounting_setup, filing, financial_docs, tax_ids, vo_csh)
      office_hub/                    # view.py + tabs (contacts, vault, notebook, setup)
      settings/                      # view.py + mixins (backup, checklist, license, pricing, workspace)
skyadmin-worker/                     # Cloudflare Worker backend (TS + Hono)
  src/                               # Hono app — routes & auth wiring
  schema.sql                         # D1 schema (12+ tables + indexes)
  migrations/                        # 0001_initial.sql
tests/                               # 53 pytest files
scripts/                             # release_check.py, publish_release.py, etc.
packaging/                           # build.cmd/.ps1, Inno Setup, Linux/macOS builds
docs/                                # ARCHITECTURE, DB_SCHEMA, ROADMAP, API_REFERENCE, etc.
```

## Key Conventions

- Python 3.10+ (3.11+ recommended)
- CustomTkinter for all UI — no Qt, no Electron, no native mobile
- SQLite with facade pattern: `Database` class composes 11 domain mixins
- Connection pooling in `db/core.py`
- Versioned migrations in `db/migrations/` (m001–m010)
- Lazy-loaded UI views — only instantiate on first access
- Services layer keeps UI thin — business logic in `services/`
- TypeScript Worker with Hono framework, D1 SQLite at edge
- Ed25519 digital signatures for licensing
- pytest for Python tests, Vitest for Worker tests
- ruff for Python linting, TypeScript strict mode for Worker

## Parallel Workstreams

- `worker-api` + `ui-widgets` (different trees)
- `desktop-core` + `ui-performance` (services vs views)
- `qa-verifier` (background) while any implementer finishes

Avoid parallel edits to the same file. `company-details` and `ui-widgets` both touch `widgets.py` — sequence those.

## What to Keep vs Fix

| Keep | Fix / improve | Do not rewrite (yet) |
|------|----------------|----------------------|
| Python `services/`, `db/` | `DatePickerField`, scroll architecture | Entire app in Kotlin/Swift |
| SQLite schema | Tab refresh, lazy loading | Worker unless API bug |
| TypeScript Worker | CustomTkinter shell performance | Full desktop framework migration |
