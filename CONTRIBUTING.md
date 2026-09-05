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

# Worker dependencies (optional)
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
- No bare `except Exception: pass` — catch specific exceptions
- Use `from __future__ import annotations` at top of every file
- Parameterized SQL only — never interpolate user input into queries
- Atomic file writes (temp + rename pattern)

### TypeScript (Worker)

- **Type checker:** `npx tsc --noEmit`
- **Tests:** `npx vitest run`
- **Strict mode** enabled
- No dynamic `import()` in hot paths

## Testing

### Python

```bash
pytest tests/ -v --tb=short
```

Tests live in `tests/` and use pytest. Run before every commit.

### Worker

```bash
cd skyadmin-worker && npm test
```

Tests live in `skyadmin-worker/src/*.test.ts` and use Vitest.

### Full pre-ship check

```bash
python scripts/release_check.py
```

This runs lint, tests, type checks, and version consistency checks.

## Architecture

```
skyadmin_pro/
├── ui/                  # CustomTkinter views and widgets
│   ├── views/           # 6 main views (dashboard, database_tasks, etc.)
│   ├── widgets.py       # Shared components (DatePickerField, etc.)
│   └── theme.py         # Colors, fonts, spacing
├── services/            # Business logic (license, crypto, export, i18n)
├── db/                  # 11 mixins → Database class (SQLite)
│   ├── core.py          # Connection pooling, _fetch_all, _fetch_one
│   ├── schema.py        # Table definitions
│   └── migrations/      # Versioned DDL changes
└── config.py            # Constants (service types, pricing, UI settings)

skyadmin-worker/         # Cloudflare Worker (TypeScript + Hono)
├── src/
│   ├── routes/          # API endpoints
│   ├── auth.ts          # Bearer token + session auth
│   ├── signing.ts       # Ed25519 + HMAC
│   └── cors.ts          # CORS middleware
└── wrangler.toml
```

### Key patterns

- **Database mixins:** Each domain (clients, tasks, tax, etc.) is a separate mixin class. The `Database` class composes all mixins via multiple inheritance.
- **View lifecycle:** `BaseView.build()` creates widgets, `on_show()`/`on_hide()` handle tab switches.
- **Lazy loading:** Views and detail trees are created on first access, not at startup.
- **Connection pooling:** Single SQLite connection reused via `_get_pooled_conn()`.

## Branch & Commit Conventions

- Branch naming: `feature/description`, `fix/description`, `refactor/description`
- Commit messages: imperative mood, <72 chars (`Add feature`, not `Added feature`)
- One logical change per commit
- Run `ruff check .` and `pytest tests/ -q` before pushing

## AI Agent Orchestration

See [AGENTS.md](AGENTS.md) for the subagent roster and parallel workstream rules.

Key rules:
- Do not rewrite the desktop UI as Kotlin/Swift/mobile native
- UI bugs are CustomTkinter layout/performance issues
- Each subagent reads its listed project skills before editing
- Run `qa-verifier` after UI or API changes

## Security

- Never commit secrets, keys, or `.dev.vars`
- Use `timingSafeEqual` for all token/secret comparisons
- Report vulnerabilities privately (see [SECURITY.md](SECURITY.md))
