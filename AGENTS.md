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
| `ui-widgets` | Date pickers, form fields, calendar popups, `widgets.py` | Form widget consistency; DatePicker regressions | `skyadmin-stack`, `skyadmin-ui-widgets` |
| `ui-performance` | Scroll jank, nested scroll, first-paint, polling | Remaining scroll/perf polish | `skyadmin-stack`, `skyadmin-ui-performance` |
| `company-details` | Company Details panel and sub-tabs | Sub-tab UX in `company_details/` | `skyadmin-stack`, `skyadmin-ui-widgets`, `skyadmin-ui-performance` |
| `worker-api` | `skyadmin-worker/` routes, sync, license, D1 | Worker routes, Vitest, D1 migrations | `skyadmin-stack`, `skyadmin-worker` |
| `desktop-core` | `services/`, `db/`, sync, export, license logic | Services/DB hardening, sync allowlists | `skyadmin-stack` |
| `qa-verifier` | After UI or API changes; pre-ship | Run pytest/vitest/release_check; report pass/fail (read-only) | `skyadmin-qa` |
| `packaging-release` | Builds, installer, CI, version bumps | Release workflow, signing, version alignment | `skyadmin-stack`, `skyadmin-qa` |

## Landed (do not re-implement)

Phases 7–11, S1 hardening, and residual sprint P0–P2 are **done**:

- `DatePickerField` transient `Toplevel` + flip-up; class-level open tracking; grab without `after(80)` / `-topmost`
- Database & Tasks active-tab-only refresh; Company Details lazy sub-tabs; Document Hub lazy panels
- Trees outside `CanvasScrollFrame` (General form scroll + fixed trees); Settings nested checklist scroll removed
- Dashboard progressive detail-tree staging on first show
- Worker timing-safe auth, sync token TTL + `token_hash`, admin CSP, control/pull rate limits
- Release publish `needs: [windows-release, worker]`; installer auto-update URL; tag fail-closed without `SKYADMIN_API_TOKEN`
- `clients.group_id` numeric FK stays local; Wave C syncs `client_groups` + `group_global_id`
- Versioned desktop migrations; thin `_migrate_*` CoreMixin wrappers removed

Do **not** re-open timing-oracle / sync-TTL / CSP / trees-out-of-scroll / release Worker gate as greenfield P0.

## Implementation priority (post residual sprint)

1. Optional polish — Filing history already expandable; further UX only if measured pain
2. Optional GitHub Environment protection on Worker deploy (concurrency already set)
3. Wave B product features — see `docs/FEATURES_AND_UPGRADE_PLAN.md`
4. Defer — deeper SQLite pool rewrite; Qt/Electron unless residual UX still fails

## Parallel workstreams

These pairs can run in parallel without conflict:

- `worker-api` + `ui-widgets` (different trees)
- `desktop-core` + `ui-performance` (services vs views)
- `packaging-release` + residual UI (workflow vs `skyadmin_pro/ui/`)
- `qa-verifier` (background) while any implementer finishes

Avoid parallel edits to the same file. `company-details` and `ui-widgets` both touch `widgets.py` — sequence those.

## What to keep vs fix

| Keep | Fix / improve | Do not rewrite (yet) |
|------|----------------|----------------------|
| Python `services/`, `db/` | Optional UX polish above | Entire app in Kotlin/Swift |
| SQLite schema + versioned migrations | `deploy.yml` concurrency | Full desktop framework migration |
| TypeScript Worker + D1 migrations | Doc drift only | Re-do S1 / P0–P2 landed work |
| Landed Phase 7–11 + S1 + P0–P2 | Feature pack F1 later | |

## Key paths

```
skyadmin_pro/ui/widgets.py              # DatePickerField, shared widgets
skyadmin_pro/ui/views/database_tasks/   # Tab view, lazy panels
skyadmin_pro/ui/views/company_details/  # Company Details sub-tabs
skyadmin_pro/ui/views/settings/         # Settings tabs
skyadmin_pro/ui/views/dashboard.py      # Dashboard
skyadmin_pro/db/migrations/             # Versioned desktop migrations
skyadmin-worker/src/                    # Worker API + Vitest
.github/workflows/release.yml           # Worker gate for publish
docs/WORKER_ADMIN.md                    # Admin UI split — multi-AI handoff
tests/                                  # pytest
skyadmin-worker/src/*.test.ts           # Vitest
docs/UI_CHECKLIST.md                    # Manual UI QA
docs/ROADMAP.md                         # Phases 7–11 (landed)
docs/MASTER_ROADMAP.md                  # Audit + backlog
```

## Success criteria

- Company Details forms usable without tree/scroll fight
- Settings: single scroll surface per tab (no nested CTk scroll)
- DatePicker multi-instance dismiss/grab polish; no `-topmost` flicker
- Dashboard first paint lighter; existing dashboard refresh tests still pass
- Tag release cannot publish if Worker Vitest fails or `SKYADMIN_API_TOKEN` missing
- Expired sync register covered by Vitest; groups sync via `global_id` / `group_global_id`
- `pytest` and Worker Vitest pass
- `python scripts/release_check.py` → RELEASE OK before ship
