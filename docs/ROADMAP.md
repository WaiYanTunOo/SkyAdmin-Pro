# SkyAdmin Pro — Product & Engineering Roadmap

Living plan after **Phase 5** (release gates, sync conflicts, auto-update, packaging, viewer PWA, Inno Setup).

**Current version:** `0.3.3` · **Primary platform:** Windows desktop

---

## Where we are today

| Area | Status |
|------|--------|
| Windows portable exe + installer | ✅ `build.ps1`, `build-installer.ps1`, `dist\SkyAdminPro-Setup-0.3.3.exe` |
| License / activation | ✅ Ed25519, claim burn, control list SKYCTRL2 |
| Worker API | ✅ Generate, revoke, sync, pricing, update, admin, viewer PWA |
| UI theme (Phases 0–4) | ✅ Form tokens, themed entries, walkthrough tests |
| Data sync | ✅ Pull/push, conflict log, mobile viewer (clients/tasks/contacts/notebook) |
| Release gate | ✅ `scripts/release_check.py`, `docs/MANUAL_QA.md` |

### Strengths to preserve

- **DB mixin architecture** (`skyadmin_pro/db/database.py`) — domain split at data layer
- **Fail-closed secrets** (`secret_fields.py`) — machine-bound Fernet
- **Export redaction** (`export.py` + `test_export_security.py`)
- **Lazy top-level views** (`main_window._ensure_view`) — only Dashboard loads at startup
- **40+ SQLite indexes** in `schema.py`

### Top complexity hotspots (split targets)

| Lines | File | Issue |
|------:|------|-------|
| ~2,000 | `ui/views/settings.py` | License, pricing, backup, sync, checklists in one class |
| ~1,200 | `services/license.py` | Verify + sync + machine ID + anti-debug mixed |
| ~1,150 | `ui/views/dashboard.py` | 10+ DB round-trips per refresh |
| ~1,100 | `ui/views/office_hub.py` | 5 tabs, no search debounce |
| ~1,100 | `ui/views/document_hub.py` | 6 tool panels in one file |
| ~690 | `skyadmin-worker/src/routes/admin/pages.ts` | Admin HTML/JS — split from `admin.ts`; see `docs/WORKER_ADMIN.md` |

**Good pattern to copy:** `database_tasks/` package split (panels per tab).

---

## Phase 7 — Stability (2–3 weeks)

**Goal:** Fewer crashes, predictable schema changes, honest error surfaces.

| # | Task | Files | Done when |
|---|------|-------|-----------|
| 7.1 | **Versioned DB migrations** — `schema_migrations` table; numbered scripts instead of `_migrate_*` chain | `db/core.py`, `db/migrations/` | New column = one migration file + test |
| 7.2 | **Dashboard query budget** — single `dashboard_snapshot()`; ≤3 SQL round-trips per refresh | `db/tax.py`, `ui/views/dashboard.py` | Regression test on query count |
| 7.3 | **Integrity banner** — show `quick_check()` failure in Settings (not only dialog) | `ui/views/settings.py` | User sees DB warning on open |
| 7.4 | **Background thread audit** — uncaught exceptions in sync/backup/export threads | `settings.py`, `document_hub.py`, `utilities.py` | Errors surface in `FeedbackLabel` | ✅ |
| 7.5 | **Single version source** | `config.py` → read by `pyproject.toml` / build scripts | No version drift |

---

## Phase 8 — Security (2–3 weeks)

**Goal:** Close licensing/sync gaps; protect credentials at rest.

| # | Task | Files | Priority |
|---|------|-------|----------|
| 8.1 | **Harden `/api/sync/register`** — reject banned/revoked/expired before issuing token | `skyadmin-worker/src/routes/sync.ts` | **P0** |
| 8.2 | **Worker route tests** — claim rate limit, sync push LWW, register rejection | `*.test.ts` | **P0** |
| 8.3 | **Encrypt `sync_device.json`** — machine-bound like `secret_fields` | `services/data_sync.py` | P1 |
| 8.4 | **Export runtime guard** — assert DataFrame columns ⊆ allowed set | `services/export.py` | P1 |
| 8.5 | **CORS review** — permissive on public routes only; tighten admin cookie routes | `skyadmin-worker/src/index.ts` | P2 |
| 8.6 | **Sync token rotation** on license renewal | `sync.ts`, desktop `data_sync.py` | P2 | ✅ |
| 8.7 | **Vault tests** — encrypt/decrypt round-trip | `tests/test_vault.py` | P1 |

---

## Phase 9 — UI/UX & code split (3–4 weeks)

**Goal:** Fast perceived load, maintainable views, consistent interaction patterns.

### 9A — Lazy loading

| # | Task | Impact |
|---|------|--------|
| 9.1 | **Database Tasks** — build tab panel only when tab selected; defer Company Details | Faster first open of DB view |
| 9.2 | **Document Hub** — lazy-init each tool panel | Faster Document Hub open |
| 9.3 | **Dashboard** — counts first, trees after `after(100)` or sub-tab click | Faster startup (Dashboard is default view) |
| 9.4 | **Office Hub debounce** — 300ms on 4 search fields | Smoother typing |

### 9B — File splits (mirror `database_tasks/`)

```
ui/views/settings/          appearance.py, license_card.py, sync_card.py, pricing_card.py, backup_card.py
ui/views/document_hub/      renamer.py, image_pdf.py, agent_bundle.py, portal.py, archive.py, financial.py
ui/views/office_hub/        contacts_tab.py, vault_tab.py, notebook_tab.py, setup_tab.py
services/license/           verify.py, online.py, machine.py  (package; monolith removed)
```

### 9C — UX polish

- Shared `ui/debounce.py` utility (used by clients, document hub, office hub)
- Loading states on Sync Now / Check updates / backup (spinner or disabled buttons)
- Empty states on all major trees
- High-DPI pass at 125% / 150% Windows scaling

---

## Phase 10 — Performance & database (2 weeks)

**Goal:** Stay smooth at 500+ clients.

| # | Task | Detail |
|---|------|--------|
| 10.1 | **FTS5 client search** | `clients_fts` virtual table; update `search_clients()` |
| 10.2 | **Treeview incremental update** | `set_rows()` full rebuild → diff by row id |
| 10.3 | **Batch sync push** on Worker | Replace per-row SELECT loop in `sync.ts` |
| 10.4 | **Composite indexes** for overdue/tax queries | `tax.py` payment_date patterns |
| 10.5 | **Perf regression tests** | `test_performance_clients.py` extended; dashboard query count |

---

## Phase 11 — Release & operations (2 weeks)

| # | Task | Detail |
|---|------|--------|
| 11.1 | **CI release job** | Windows runner builds exe on git tag; artifact upload |
| 11.2 | **Windows code signing** | `packaging/sign-windows.ps1` in build + CI |
| 11.3 | **macOS notarization** | Document + script in `packaging/build-macos.sh` |
| 11.4 | **Worker D1 migrations** | Numbered SQL files instead of full `schema.sql` replay |
| 11.5 | **Changelog** | `CHANGELOG.md` + `scripts/generate_changelog.py` |
| 11.6 | **Publish pipeline** | tag → build → release_check → GitHub Release → `publish_update.py` |

---

## Quick wins (do anytime, 1–3 days each)

- [x] Align `pyproject.toml` to `0.3.1`
- [x] Inno Setup installed + `dist\SkyAdminPro-Setup-0.3.1.exe`
- [x] Debounce Office Hub search (`office_hub.py` + `ui/debounce.py`)
- [x] Ban/revoke/expiry checks on sync register + claim (`sync_eligibility.ts`)
- [x] Lazy-load Company Details + Suppliers tabs (`database_tasks/view.py`)
- [x] Dashboard snapshot — no duplicate expiring queries (`tax.py`, `dashboard.py`)
- [x] Vitest for sync register + eligibility (`sync.test.ts`)
- [x] Encrypt `sync_device.json` at rest (`data_sync.py`)
- [x] Export runtime column guard (`export.py`)
- [x] Vault round-trip tests (`tests/test_vault.py`)
- [x] Document Hub lazy tab panels (`document_hub.py`)
- [x] FTS5 client search (`core.py`, `clients.py`)
- [x] Batch sync push on Worker (`sync_push.ts`) (Phase 10.3)
- [x] Composite overdue/ongoing indexes + migration 008 (Phase 10.4)
- [x] Perf regression tests — overdue + dashboard query budget (Phase 10.5)
- [x] CI release workflow (`.github/workflows/release.yml`)
- [x] Changelog + release notes generator (`CHANGELOG.md`, `scripts/generate_changelog.py`) (Phase 11.5)
- [x] Publish pipeline — GitHub Release + Worker update on tag (`release.yml`, `scripts/publish_release.py`) (Phase 11.6)
- [x] Split `settings.py` into package (Phase 9B)
- [x] Settings integrity banner on open (Phase 7.3)
- [x] Dashboard deferred tree refresh + expanded snapshot (Phase 7.2 / 9.3)
- [x] Sync column allowlist + worker push/pull hardening (Phase 8)
- [x] Admin API CSRF fix — Bearer **or** same-origin cookie+CSRF; CORS credentials same-origin only (Phase 8.5)
- [x] Office Hub lazy tabs (Phase 9.1)
- [x] Filing status save debounce 300ms (Phase 9C)
- [x] Sync token rotation on license save / re-register (`sync.ts`, `data_sync.py`) (Phase 8.6)
- [x] Split `services/license.py` into package (`license/machine.py`, `online.py`, `verify.py`) (Phase 9B)
- [x] High-DPI scaling bootstrap (`ui/display.py`, `main.py`) (Phase 9C)
- [x] Tree empty states + backup button loading guard (Phase 9C)
- [x] Sync/updates loading states + thread error surfacing (`license_mixin.py`, `async_ui.py`) (Phase 9C / 7.4)
- [x] Single version source — `APP_VERSION` reads `pyproject.toml` (Phase 7.5)
- [x] Split `admin.ts` into `routes/admin/` package (`handler`, `session`, `pages`) — see `docs/WORKER_ADMIN.md`

---

## Recommended execution order

```mermaid
flowchart LR
    QW[Quick wins] --> P7[Phase 7 Stability]
    P7 --> P8[Phase 8 Security]
    P8 --> P9[Phase 9 UI split + lazy load]
    P9 --> P10[Phase 10 DB perf]
    P10 --> P11[Phase 11 Release ops]
```

1. **Quick wins + Phase 8.1** — sync register hardening (highest security risk)
2. **Phase 7.2** — dashboard query storm (worst daily UX pain)
3. **Phase 9.1–9.4** — lazy tabs + debounce (visible speed)
4. **Phase 9B** — split `settings.py` then `document_hub.py` (maintainability)
5. **Phase 10** — FTS5 when client count becomes painful
6. **Phase 11** — signing + CI artifacts before wide distribution

---

## Success metrics

| Metric | Target |
|--------|--------|
| pytest + vitest | 100% pass on CI |
| `release_check.py` | RELEASE OK before every ship |
| Dashboard refresh | ≤3 SQL queries |
| First open Database Tasks | <500ms to interactive tab (lazy) |
| Client search (500 rows) | <100ms perceived (debounce + FTS) |
| Security | Banned machine cannot obtain sync token |
| Manual QA | `docs/MANUAL_QA.md` sign-off on clean PC |

---

## Related docs

- [PLATFORM.md](PLATFORM.md) — cross-platform strategy
- [MANUAL_QA.md](MANUAL_QA.md) — pre-ship checklist
- [UI_CHECKLIST.md](UI_CHECKLIST.md) — theme/layout automation
- [PHASE4_WALKTHROUGH.md](PHASE4_WALKTHROUGH.md) — per-view UI pass
- [packaging/README.md](../packaging/README.md) — build & installer
