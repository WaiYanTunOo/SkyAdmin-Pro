# SkyAdmin Pro — Agent orchestration

## Stack (do not rewrite as mobile native)

| Layer | Technology |
|-------|------------|
| Desktop UI | Python 3 + CustomTkinter |
| Database | SQLite (`skyadmin_pro/db/`) |
| Backend API | TypeScript Cloudflare Worker (`skyadmin-worker/`) |
| Packaging | PyInstaller (Windows-focused) |

**Not in scope:** Kotlin/Swift/Android/iOS UI. UI bugs are CustomTkinter layout/performance issues, not missing native mobile code.

## Subagent roster

Delegate using the Task tool or `/subagent-name`. Each subagent reads its listed project skills before editing.

| Subagent | When to delegate | Primary duties | Skills |
|----------|------------------|----------------|--------|
| `ui-widgets` | Date pickers, form fields, calendar popups, `widgets.py` | Fix `DatePickerField` clipping; transient `Toplevel` popups; form widget consistency | `skyadmin-stack`, `skyadmin-ui-widgets` |
| `ui-performance` | Scroll jank, tab refresh storms, lazy loading, polling | Active-tab-only refresh; pause hidden polling; reduce nested `CTkScrollableFrame` | `skyadmin-stack`, `skyadmin-ui-performance` |
| `company-details` | Company Details panel and sub-tabs | Lazy sub-tab build; scroll architecture in `company_details/` | `skyadmin-stack`, `skyadmin-ui-widgets`, `skyadmin-ui-performance` |
| `worker-api` | `skyadmin-worker/` routes, sync, license, D1 | Worker routes, Vitest, wrangler deploy patterns | `skyadmin-stack`, `skyadmin-worker` |
| `desktop-core` | `services/`, `db/`, sync, export, license logic | Business logic and SQLite; keep UI thin | `skyadmin-stack` |
| `qa-verifier` | After UI or API changes; pre-ship | Run pytest/vitest/release_check; report pass/fail (read-only) | `skyadmin-qa` |
| `packaging-release` | Builds, installer, CI, version bumps | PyInstaller, Inno Setup, `release_check.py`, GitHub workflows | `skyadmin-stack`, `skyadmin-qa` |

## Implementation priority (from reality check)

1. `ui-widgets` — `DatePickerField` transient Toplevel + flip-up near screen bottom
2. `ui-performance` — `database_tasks/view.py` active-tab-only refresh
3. `company-details` — lazy sub-tab creation in `company_details/panel.py`
4. `company-details` + `ui-performance` — simplify scroll nesting in Company Details tabs
5. `ui-performance` — Dashboard/Document Hub lazy load + pause polling
6. Re-evaluate; **do not** start Qt/Electron migration unless Phase 1–2 fail

## Parallel workstreams

These pairs can run in parallel without conflict:

- `worker-api` + `ui-widgets` (different trees)
- `desktop-core` + `ui-performance` (services vs views)
- `qa-verifier` (background) while any implementer finishes

Avoid parallel edits to the same file. `company-details` and `ui-widgets` both touch `widgets.py` — sequence those.

## What to keep vs fix

| Keep | Fix / improve | Do not rewrite (yet) |
|------|----------------|----------------------|
| Python `services/`, `db/` | `DatePickerField`, scroll architecture | Entire app in Kotlin/Swift |
| SQLite schema | Tab refresh, lazy loading | Worker unless API bug |
| TypeScript Worker | CustomTkinter shell performance | Full desktop framework migration |

## Key paths

```
skyadmin_pro/ui/widgets.py              # DatePickerField, shared widgets
skyadmin_pro/ui/views/database_tasks/   # Tab view, lazy panels
skyadmin_pro/ui/views/company_details/  # Company Details sub-tabs
skyadmin_pro/ui/views/dashboard.py      # Dashboard refresh budget
skyadmin_pro/ui/views/document_hub.py   # Polling, tool panels
skyadmin-worker/src/                    # Worker API
docs/WORKER_ADMIN.md                    # Admin UI split — multi-AI handoff
tests/                                  # pytest
skyadmin-worker/src/*.test.ts           # Vitest
docs/UI_CHECKLIST.md                    # Manual UI QA
docs/ROADMAP.md                         # Phases 7–11
```

## Success criteria

- Expiry date picker fully visible (no clip inside scroll frames)
- Database & Tasks tab switch does not refresh all 8 panels
- Company Details sub-tabs build on first visit
- `pytest` and Worker Vitest pass
- `python scripts/release_check.py` → RELEASE OK before ship
