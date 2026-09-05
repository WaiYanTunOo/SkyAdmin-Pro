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
| `ui-widgets` | Date pickers, form fields, calendar popups, `widgets.py` | DatePicker polish (multi-instance binds, grab, topmost); form widget consistency | `skyadmin-stack`, `skyadmin-ui-widgets` |
| `ui-performance` | Scroll jank, nested scroll, first-paint, polling | Trees out of scroll; Settings nested scroll; Dashboard first-paint deferral | `skyadmin-stack`, `skyadmin-ui-performance` |
| `company-details` | Company Details panel and sub-tabs | Trees outside `CanvasScrollFrame`; scroll architecture in `company_details/` | `skyadmin-stack`, `skyadmin-ui-widgets`, `skyadmin-ui-performance` |
| `worker-api` | `skyadmin-worker/` routes, sync, license, D1 | Expired register Vitest; auth/doc wording; Worker routes | `skyadmin-stack`, `skyadmin-worker` |
| `desktop-core` | `services/`, `db/`, sync, export, license logic | Finish `_migrate_*` extract; `group_id` sync allowlist; vault/ciphertext tests | `skyadmin-stack` |
| `qa-verifier` | After UI or API changes; pre-ship | Run pytest/vitest/release_check; report pass/fail (read-only) | `skyadmin-qa` |
| `packaging-release` | Builds, installer, CI, version bumps | Release Worker gate (`needs: worker`); version hardcode alignment | `skyadmin-stack`, `skyadmin-qa` |

## Landed (do not re-implement)

Phases 7–11 quick wins and AGENTS priorities 1–3 are **done**:

- `DatePickerField` transient `Toplevel` + flip-up near screen bottom
- Database & Tasks active-tab-only refresh
- Company Details lazy sub-tab creation
- Document Hub lazy panels + poll pause
- Worker timing-safe auth, sync token TTL, admin CSP (and related S1 hardening)

Do **not** re-open timing-oracle / sync-TTL / CSP work as greenfield P0.

## Implementation priority (residual sprint backlog)

1. `company-details` + `ui-performance` — Company Details: keep trees **outside** `CanvasScrollFrame` (form scroll vs tree)
2. `ui-performance` — Settings: remove nested `CTkScrollableFrame` checklist scroll
3. `ui-widgets` — DatePicker polish (class-level open-popup tracking, safer grab, drop `-topmost` flicker)
4. `ui-performance` — Dashboard: defer more of first `build()` cost (stat cards stay; heavy widgets later)
5. `packaging-release` — Gate GitHub Release / Worker update on Worker job success (`needs: worker`)
6. `worker-api` — Vitest for expired claim eligibility on `POST /api/sync/register` → 403
7. `desktop-core` — Extract remaining `_migrate_*` into `db/migrations/`; add `group_id` to sync allowlists (or document local-only)

Re-evaluate after this backlog; **do not** start Qt/Electron migration unless residual UX still fails after these fixes.

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
| Python `services/`, `db/` | Trees-out-of-scroll, Settings nested scroll | Entire app in Kotlin/Swift |
| SQLite schema | DatePicker polish, Dashboard first-paint | Worker unless API/test gap |
| TypeScript Worker | Release Worker gate; migrate extract; `group_id` sync | Full desktop framework migration |
| Landed Phase 7–11 + S1 hardening | Expired-register Vitest | Re-do timing oracle / sync TTL / CSP |

## Key paths

```
skyadmin_pro/ui/widgets.py              # DatePickerField, shared widgets
skyadmin_pro/ui/views/database_tasks/   # Tab view, lazy panels
skyadmin_pro/ui/views/company_details/  # Company Details sub-tabs
skyadmin_pro/ui/views/settings/         # Nested scroll residual
skyadmin_pro/ui/views/dashboard.py      # Dashboard first-paint
skyadmin_pro/db/migrations/             # Remaining _migrate_* extract
skyadmin-worker/src/                    # Worker API + Vitest
.github/workflows/release.yml           # Worker gate for publish
docs/WORKER_ADMIN.md                    # Admin UI split — multi-AI handoff
tests/                                  # pytest
skyadmin-worker/src/*.test.ts           # Vitest
docs/UI_CHECKLIST.md                    # Manual UI QA
docs/ROADMAP.md                         # Phases 7–11 (landed)
docs/MASTER_ROADMAP.md                  # Audit + current NEXT backlog
```

## Success criteria

- Company Details forms usable without tree/scroll fight
- Settings: single scroll surface per tab (no nested CTk scroll)
- DatePicker multi-instance dismiss/grab polish; no `-topmost` flicker
- Dashboard first paint lighter; existing dashboard refresh tests still pass
- Tag release cannot publish if Worker Vitest fails
- Expired sync register covered by Vitest; `group_id` sync intentional
- `pytest` and Worker Vitest pass
- `python scripts/release_check.py` → RELEASE OK before ship
