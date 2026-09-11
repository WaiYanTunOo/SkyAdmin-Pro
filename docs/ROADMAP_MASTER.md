# SkyAdmin Pro — Master Roadmap (Feature-Tracked)

**Version:** `0.3.3` · **Updated:** 2026-09-11

Consolidated roadmap organized by feature. Each row links to the feature detail file.

> **Status legend:** ✅ Landed · ⚠️ Partial · ⏳ Planned · ❌ Deferred · 🚫 Do-not-reopen

---

## Feature Roadmap

### F1. Dashboard
[Detail →](features/dashboard.md) · Files: `ui/views/dashboard.py`, `db/tax.py`, `services/tracking.py`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Dashboard query budget — `dashboard_snapshot()` single connection | 7.2 | ⚠️ Partial (≤40 stmts/1 conn; ≤3 SQL rewrite deferred) |
| Dashboard progressive detail trees on `on_show` | 9.3 | ✅ Landed |
| Dashboard Export PDF + tax overview | Wave A F1.6 | ✅ Landed |
| Dashboard first-paint measurement test | Wave A A4 | ✅ Landed |

**Next:** Deeper Dashboard SQL ≤3 rewrite (Wave D D4, optional).

---

### F2. Database & Tasks
[Detail →](features/database_tasks.md) · Files: `ui/views/database_tasks/*`, `db/{clients,tasks,suppliers,courier,pipeline,financial}.py`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Lazy tab panel build (clients, company, suppliers) | 9.1 | ✅ Landed |
| Active-tab-only refresh | Residual | ✅ Landed |
| Empty states on trees | 9C | ✅ Landed |
| Bulk client operations (multi-select → status/group/archive) | Wave B F1.3 | ✅ Landed |
| Client grouping UX (`client_groups`) | Wave B F1.4 | ✅ Landed |

**Next:** Optional UX polish only.

---

### F3. Company Details
[Detail →](features/company_details.md) · Files: `ui/views/company_details/*`, `services/{tax_ids,vo_csh}_rollout.py`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Split into per-tab files (9B pattern) | 9B | ✅ Landed |
| Trees outside `CanvasScrollFrame` (forms-only scroll) | U1.0a | ✅ Landed |
| Filing history expandable row | Residual | ✅ Landed |
| Filing status save debounce 300ms | 9C | ✅ Landed |
| Audit log surfaces (tax cycle + sync conflicts) | Wave B F1.5 | ✅ Landed |

**Next:** Consolidate redundant refresh dispatch (U1.2) — optional.

---

### F4. Document Hub
[Detail →](features/document_hub.md) · Files: `ui/views/document_hub/*`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Lazy-init each tool panel | 9.2 | ✅ Landed |
| Poll pauses when hidden | Residual | ✅ Landed |
| Background thread error surfacing | 7.4 | ✅ Landed |
| 6 tool panels split from single file | 9B | ✅ Landed |

**Next:** Cache folder listing if network drives (P3, optional).

---

### F5. Office Hub
[Detail →](features/office_hub.md) · Files: `ui/views/office_hub/*`, `db/office.py`, `services/vault.py`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Lazy tabs | 9.1 | ✅ Landed |
| 300ms search debounce | 9.4 | ✅ Landed |
| File splits into per-tab files | 9B | ✅ Landed |
| Office Hub rollout | Residual | ✅ Landed |

**Next:** None (polished).

---

### F6. Settings
[Detail →](features/settings.md) · Files: `ui/views/settings/*`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Split into package (5 mixins) | 9B | ✅ Landed |
| General eager, others lazy | Residual | ✅ Landed |
| Integrity banner on open | 7.3 | ✅ Landed |
| Nested checklist scroll removed | U1.0b | ✅ Landed |
| Sync/loading states | 9C | ✅ Landed |

**Next:** None (polished).

---

### F7. UI Widgets
[Detail →](features/ui_widgets.md) · Files: `ui/widgets.py`, `ui/treeview.py`, `ui/canvas_scroll.py`, `ui/theme.py`, `ui/display.py`, `ui/debounce.py`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| DatePicker transient Toplevel + flip-up | Residual | ✅ Landed |
| DatePicker multi-instance root binds, grab without `-topmost` | U1.1 | ✅ Landed |
| CanvasScrollFrame smoother than CTkScrollableFrame | U1.0a | ✅ Landed |
| Virtual scrolling at 60 rows, incremental at 20 | 10.2 | ✅ Landed |
| High-DPI scaling bootstrap | 9C | ✅ Landed |
| Tree empty states | 9C | ✅ Landed |
| Treeview theme caching | Residual | ✅ Landed |

**Next:** Cache `apply_form_theme()` (P1); narrow bare excepts (P0).

---

### F8. Licensing & Activation
[Detail →](features/licensing.md) · Files: `services/license/*`, `ui/activation.py`, `main.py`, Worker `routes/{generate,claim,control,revoke,ban,used,records}.ts`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Split `services/license.py` into package | 9B | ✅ Landed |
| Sync register hardening (reject banned/revoked/expired) | 8.1 | ✅ Landed |
| Sync token rotation on renewal | 8.6 | ✅ Landed |
| Timing-safe admin/API compares | S1 | ✅ Landed |
| Admin login rate limiting | S1 | ✅ Landed |
| CSP on admin/viewer pages | S1 | ✅ Landed |
| Test-key-only label on dev key | S1 | ✅ Landed |
| Admin session flow tests | S2.1 | ✅ Landed |
| Rate limit tests | S2.2 | ✅ Landed |
| Worker integration test (generate→claim→verify) | S2.4 | ✅ Landed |

**Next:** `generate.ts` static imports + D1 insert-audit (P2); `verify.py` monolith refactor.

---

### F9. Data Sync
[Detail →](features/data_sync.md) · Files: `services/{data_sync,sync_schema,sync_hlc}.py`, Worker `sync_*.ts`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Encrypt `sync_device.json` at rest | 8.3 | ✅ Landed |
| Sync token TTL + `token_hash` | S1 | ✅ Landed |
| Expired sync register rejected (Vitest) | Residual | ✅ Landed |
| Batch sync push on Worker | 10.3 | ✅ Landed |
| Sync column allowlist (`group_id` excluded) | 8 / Wave C | ✅ Landed |
| Pull pagination UX | Wave C C2 | ✅ Landed |
| Conflict review UI | Wave C C3 | ✅ Landed |
| `client_groups` sync via `global_id` | Wave C C1 | ✅ Landed |
| HLC ordering migration m012 | Wave C | ✅ Landed |

**Next:** LIMIT interpolation hardening (`sync.ts:132`, P2); plaintext fallback log+re-encrypt (P3).

---

### F10. Export & Reports
[Detail →](features/export_reports.md) · Files: `services/{export,reports,pdf_render,importer}.py`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Export runtime column guard | 8.4 | ✅ Landed |
| Print-ready reports incl. tax overview | Wave B F1.6 | ✅ Landed |
| Atomic temp+rename writes | — | ✅ Landed |

**Next:** None (polished).

---

### F11. Backup & Restore
[Detail →](features/backup_restore.md) · Files: `services/auto_backup.py`, `db/core.py`, `ui/views/settings/backup_mixin.py`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Scheduled auto-backup UX (retention, folder, toast) | Wave B F1.1 | ✅ Landed |
| Restore closes pool before overwrite | Residual | ✅ Landed |
| Fernet-encrypted backups, keep 7 | — | ✅ Landed |

**Next:** None (polished).

---

### F12. Security & Crypto
[Detail →](features/security_crypto.md) · Files: `services/{secret_fields,vault,crypto,_protect_core,_secret}.py`, `db/cipher.py`, Worker `{auth,cors,csp,timing_safe,rate_limit,admin_security}.ts`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Fail-closed secrets (machine-bound Fernet) | — | ✅ Landed |
| CORS review (same-origin credentials) | 8.5 | ✅ Landed |
| CSP all HTML responses | S1 | ✅ Landed |
| Timing-safe auth (no `===`) | S1 | ✅ Landed |
| `rate_limits` table cleanup on Nth request | S1 | ✅ Landed |
| Vault round-trip tests | 8.7 | ✅ Landed |
| Login attempt cleanup on success | S2/S11 | ✅ Landed |

**Next:** Full HMAC seal (`_protect_core.py:78`, P1); bare-except narrowing (P0).

---

### F13. i18n & Translation
[Detail →](features/i18n.md) · Files: `services/{i18n,translate,snippets}.py`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Language switch (EN/MY/TH) | — | ✅ Landed |
| Snippet packs (versioned `snippet_versions`) | — | ✅ Landed |
| i18n / translate tests | T1.2 | ✅ Landed |

**Next:** Thread-safe `_current_lang` lock (P1); per-request socket timeout (P2).

---

### F14. Database Layer
[Detail →](features/database_layer.md) · Files: `db/*.py` + `db/migrations/*`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Versioned DB migrations (`schema_migrations`) | 7.1 | ✅ Landed |
| `_migrate_*` wrappers removed (thin CoreMixin) | Residual | ✅ Landed |
| FTS5 client search | 10.1 | ✅ Landed |
| Composite overdue/ongoing indexes (m008) | 10.4 | ✅ Landed |
| Perf regression tests (overdue + dashboard budget) | 10.5 | ✅ Landed |
| Client groups m009 + sync m011 | Wave C | ✅ Landed |
| HLC m012 | Wave C | ✅ Landed |

**Next:** SQLite connection pooling (P1.1 — ❌ deferred until measured pain); snapshot ≤3 rewrite (optional).

---

### F15. Config
[Detail →](features/config.md) · Files: `config/*`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Single version source (`APP_VERSION` from pyproject) | 7.5 | ✅ Landed |
| Domain split into 8 modules | — | ✅ Landed |

**Next:** Extract checklist data + shrink `__init__.py` (P1).

---

### F16. Cloudflare Worker
[Detail →](features/worker_api.md) · Files: `skyadmin-worker/src/**`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| Worker route tests (claim, sync push, register) | 8.2 | ✅ Landed |
| Admin timing oracles fixed (S1) | S1 | ✅ Landed |
| D1 migration framework `0001–0007` | 11.4 | ✅ Landed |
| Admin split → `routes/admin/` pkg | 9B / WORKER_ADMIN | ✅ Landed |
| Worker Vitest gates release publish | R1.0 | ✅ Landed |
| Deploy concurrency group | Residual | ✅ Landed |

**Next:** `recordsHandler` JOIN optimization (P1); staging worker env (Wave D D2); dependency/SAST scanning.

---

### F17. CI/CD & Packaging
[Detail →](features/cicd_packaging.md) · Files: `.github/workflows/*`, `scripts/*`, `packaging/*`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| CI release job (Windows runner on tag) | 11.1 | ✅ Landed |
| Windows code signing | 11.2 | ✅ Landed |
| Changelog + generator | 11.5 | ✅ Landed |
| Publish pipeline → GitHub Release + Worker | 11.6 | ✅ Landed |
| Release gate `needs: worker` | R1.0 | ✅ Landed |
| Tag fail-closed without `SKYADMIN_API_TOKEN` | Residual | ✅ Landed |

**Next:** Dependency vulnerability scan (P1); SAST (P2); macOS notarization (Wave D D1).

---

### F18. Utilities
[Detail →](features/utilities.md) · Files: `services/{file_ops,workflow,undo_manager,column_state,process_jobs,remote_pricing,data_hygiene,tax_calendar,tracking,net,storage_backend,client_commands}.py`

| Roadmap item | Phase | Status |
|-------------|-------|--------|
| File ops tests | T1.1 | ✅ Landed |
| Hadoop → none; all utilities tested | T1 | ✅ Landed |

**Next:** `file_ops.py:196` Popen path validation (P1).

---

## Fix Backlog (feature-tagged)

| # | Pri | Issue | File:Line | Feature | Phase |
|---|-----|-------|-----------|---------|-------|
| 1 | P0 | SQLite connection per query — no pooling | `db/core.py:40–72` | F14 | P1.1 |
| 2 | P0 | Dashboard snapshot 12+ connections | `db/tax.py:158–179` | F1 | P1.2 |
| 3 | P0 | 100+ bare `except Exception: pass` | `ui/widgets.py`, `display.py`, `canvas_scroll.py`, `treeview.py`, `main_window.py` | F7/F12 | Q1 |
| 4 | P1 | Config monolith (checklist data embedded) | `config/__init__.py:189–301` | F15 | Q2 |
| 5 | P1 | 7-mixin MRO complexity | `company_details/panel.py:57–74` | F3 | U8 |
| 6 | P1 | `_fetch_all`/`_fetch_one` in wrong mixin | `db/clients.py:329–337` | F14 | Q4 |
| 7 | P1 | Thread-unsafe `_current_lang` global | `services/i18n.py:59` | F13 | S19 |
| 8 | P1 | Worker `recordsHandler` full table scan | `routes/records.ts:24–29` | F16 | P8 |
| 9 | P1 | HMAC integrity seal truncated 64 bits | `services/_protect_core.py:78` | F12 | S18 |
| 10 | P1 | `apply_form_theme()` recursive walk on view switch | `widgets.py:142–165` | F7 | P3 |
| 11 | P1 | `subprocess.Popen` user-influenced paths | `services/file_ops.py:196–198` | F18 | S13 |
| 12 | P2 | Private `_views` accessed across modules | `panel.py:930–932`, `dashboard.py:1092` | F3/F1 | U10 |
| 13 | P2 | String-based tab dispatch | `database_tasks/view.py`, `company_details/panel.py` | F2/F3 | U11 |
| 14 | P2 | `__import__()` inline imports | `treeview.py:130–133`, 9+ files | F7 | Q5–6 |
| 15 | P2 | Dynamic `import()` hot path | `routes/generate.ts:25–27` | F8 | P9 |
| 16 | P2 | License returned before DB insert confirmed | `routes/generate.ts:53–55` | F8 | P11 |
| 17 | P2 | Duplicate license constants | `license/_constants.py` vs `machine.py` | F8 | Q3 |
| 18 | P2 | SQL LIMIT interpolation | `routes/sync.ts:132` | F9 | S12 |
| 19 | P2 | `translate.py` global socket timeout | `services/translate.py:41–56` | F13 | P6 |
| 20 | P2 | `vo_csh_rollout.py` duplicated inference | `services/vo_csh_rollout.py:77–116` | F3 | Q9 |
| 21 | P3 | Plaintext credential fallback | `services/data_sync.py:86–91` | F9 | S15 |
| 22 | P3 | `pyarmor.bug.log` in repo root | root | F12 | S21 |
| 23 | P3 | Dead `@ts-ignore` branch | `worker/src/auth.ts:16–19` | F12 | S23 |

---

## Closed Items (do not re-implement)

- ✅ Timing-safe admin/API compares — **S1 done**
- ✅ Sync token TTL + rotation + token_hash — **S1 done**
- ✅ Admin/viewer CSP — **S1 done**
- ✅ Trees-out-of-scroll (Company Details, Settings checklist) — **U1.0 done**
- ✅ DatePicker Toplevel/grab/flip-up, no `-topmost` — **U1.1 done**
- ✅ Dashboard progressive detail trees — **P1.4 done**
- ✅ Release `needs: worker` Worker gate — **R1.0 done**
- ✅ Installer auto-update URL; tag fail-closed — **residual done**
- ✅ `_migrate_*` wrappers removed; versioned migrations — **P1.3 done**
- ✅ Wave C sync (`client_groups`, pagination, conflict review) — **done**

## Priority Order (post residual sprint)

1. Optional UX polish (Filing history weight, Settings lazy tabs) — already landed
2. Optional GitHub Environment `production` on `deploy.yml` (concurrency set)
3. Wave B product features — landed in tree
4. **QA** — pytest + Vitest + `release_check` before ship
5. **Defer** — deeper SQLite pooling; Qt/Electron unless residual UX still fails

---

## Related

- [ROADMAP.md](ROADMAP.md) — Phase 7–11 detail
- [MASTER_ROADMAP.md](MASTER_ROADMAP.md) — full audit + checkboxes
- [FEATURES_AND_UPGRADE_PLAN.md](FEATURES_AND_UPGRADE_PLAN.md) — product inventory + waves
- [FEATURE_MAP.md](FEATURE_MAP.md) — quick file lookup per feature
- [ARCHITECTURE.md](ARCHITECTURE.md) — system diagram
