# Contributing to SkyAdmin Pro

Proprietary software — contribution is by invitation only. This document
covers conventions for internal developers and AI agents.

## Development Setup

### Requirements

- Python 3.10+ (3.11+ recommended)
- Node.js 22+ (for Worker tests)
- Windows 10/11 (primary target platform)

### Quick start

```bash
# Python dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run the app
python main.py

# Worker dependencies
cd skyadmin-worker && npm ci
```

## Code Style

### Python

- **Linter:** `ruff check .`
- **Formatter:** `ruff format .`
- **Line length:** 120 characters
- **Import order:** `ruff` isort (first-party: `skyadmin_pro`)
- **Target:** Python 3.10+ syntax

Key rules:

- Prefer specific exceptions over broad `except Exception`
- Use `from __future__ import annotations` at top of modules
- Parameterized SQL only — never interpolate user input into queries
- Atomic file writes (temp + rename pattern)
- Fail closed for secrets/export/license verify (`secret_fields`, export redaction, Ed25519)

### TypeScript (Worker)

- **Type checker:** `npx tsc --noEmit`
- **Tests:** `npm test` (Vitest)
- **Strict mode** enabled
- Add Vitest coverage for route/behavior changes
- D1 changes go in `skyadmin-worker/migrations/` — do **not** use `db:init` / `schema.sql` apply

## Testing

### Python

```bash
pytest tests/ -q --tb=short
```

### Worker

```bash
cd skyadmin-worker && npm test
```

### Full pre-ship check

```bash
python scripts/release_check.py
# Portable-only builds may use: --skip-installer --skip-pytest
```

Manual UI: `docs/UI_CHECKLIST.md`, `docs/MANUAL_QA.md`.

## Architecture (short)

```
skyadmin_pro/
├── ui/                  # CustomTkinter views and widgets
│   ├── views/           # dashboard, database_tasks, company_details, settings, …
│   ├── widgets.py       # DatePickerField, FormField, themed controls
│   └── canvas_scroll.py # Form scroll (trees stay outside)
├── services/            # license, data_sync, export, vault, i18n
├── db/                  # Database mixins + versioned migrations/
└── config/              # APP_VERSION, settings keys, pricing defaults

skyadmin-worker/         # Cloudflare Worker (TypeScript + Hono)
├── src/routes/          # API + admin HTML
├── migrations/          # D1 versioned SQL
└── wrangler.jsonc
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for diagrams and data flow.

### Key patterns

- **Database mixins:** Domain mixins compose into `Database`.
- **View lifecycle:** `BaseView.build()` creates widgets; `on_show()` / `on_hide()` on tab switch.
- **Lazy loading:** Company Details / Settings / Document Hub build heavy panels on first visit.
- **Scroll:** One scroll surface per tab; trees outside `CanvasScrollFrame`.
- **Connection pooling:** Thread-local pooled SQLite connections in `db/core.py`.

## Branch & Commit Conventions

- Branch naming: `feature/…`, `fix/…`, `refactor/…`
- Commit messages: imperative mood, ≤72 char subject
- One logical change per commit
- Run `ruff check .` and `pytest -q` (and Worker `npm test` if touching `skyadmin-worker/`) before push

## AI Agent Orchestration

See [AGENTS.md](AGENTS.md) for the subagent roster and parallel workstream rules.

- Do **not** rewrite the desktop UI as Kotlin/Swift/Qt/Electron unless explicitly requested after residual UX still fails
- Do **not** re-implement landed S1 / P0–P3 items (timing-safe auth, sync TTL/hash, trees-out-of-scroll, release Worker gate, etc.)
- Run `qa-verifier` after UI or API changes

## Security

- Never commit secrets, keys, or `.dev.vars`
- Use `timingSafeEqual` for secret/token comparisons
- Report vulnerabilities privately — [SECURITY.md](SECURITY.md)

## Deploy notes

- Tag releases: `.github/workflows/release.yml` requires Worker Vitest + `SKYADMIN_API_TOKEN`
- Main Worker deploys: `.github/workflows/deploy.yml` (concurrency group; migrations then deploy)
- After D1 `0003_sync_tokens_hash`, devices must **re-register** for sync
