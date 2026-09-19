# SkyAdmin Pro — Comprehensive Fix & Hardening Plan

**Version:** 0.3.3+ · **Status:** Active

Based on thorough codebase analysis. Most major work (Phases 7-11, S1, P0-P3) is landed. This targets residual gaps.

## Health Scores
| Layer | Score | Top Concern |
|-------|-------|-------------|
| Cloudflare Worker | 8.5/10 | Missing integration tests; SQL LIMIT interpolation |
| Desktop Core (DB) | 7.5/10 | Connection pooling not fully implemented |
| Desktop Core (Services) | 8/10 | 100+ bare excepts; __import__ calls |
| UI/UX | 8.5/10 | apply_form_theme walk; DatePicker fragility |
| Security | 9/10 | S1 hardening done; residual cleanups only |
| Testing | 7/10 | Missing admin session, rate-limit, integration tests |
| CI/CD | 9/10 | Well-gated; add SAST/dependency scanning maturity |
| Config | 7/10 | __init__.py still large; doc drift |
| Documentation | 8/10 | Most docs exist; verify drift |

## 1. Cloudflare Worker

### 1.1 Critical — SQL / Query Quality
- W-01: SQL LIMIT interpolation in `routes/sync.ts:132` → parameterized integer cast
- W-02: `recordsHandler` subquery pattern → LEFT JOIN in `routes/records/query.ts`
- W-03: `generate.ts` returns license before D1 insert → move return after insert

### 1.2 Security
- W-04: SQL LIMIT interpolation (also W-01)
- W-05: `subprocess.Popen` user-influenced paths → verify fix + regression test
- W-06: Plaintext credential fallback → log warning; re-encrypt
- W-07: `pyarmor.bug.log` in repo root → add to .gitignore; delete

### 1.3 Testing Gaps
- W-08: Admin session flow → `src/admin.test.ts`
- W-09: Rate limiting → `src/rate_limit.test.ts`
- W-10: CORS behavior → `src/cors.test.ts`
- W-11: Full HTTP lifecycle → `src/lifecycle.test.ts`
- W-12: Pricing POST → `src/pricing.test.ts`
- W-13: Handler tests → `src/handlers.test.ts`
- W-14: Expired sync register → `src/sync_eligibility.test.ts`

### 1.4 Worker Operational
- W-15: Staging environment needs real D1 ID
- W-16: Deploy concurrency verification
- W-17: Worker typecheck/vitest gate verification

## 2. Desktop Core — DB
- D-01: Connection per query → audit `_connect()` calls, ensure `_get_pooled_conn()` everywhere
- D-02: `dashboard_snapshot()` 12+ connections → single connection
- D-03: Background thread connection leaks
- D-04: 100+ bare `except Exception: pass` → narrow exceptions
- D-05: `__import__()` inline → top-level imports
- D-06: Duplicate license constants → single source
- D-07: `config/__init__.py` 224 lines → further split
- D-08: `format_thousands()` doesn't accept str

## 3. Desktop Core — Services
- D-09: `translate.py` global socket timeout → per-request
- D-10: Thread-unsafe `_current_lang` → verify fix + regression
- D-11: `vo_csh_rollout.py` duplicated inference → refactor
- D-12: XOR obfuscation → document as non-security boundary

## 4. UI/UX
- U-01: DatePicker `_try_grab` after 80ms → immediate grab
- U-02: DatePicker scroll position → verify with CanvasScrollFrame
- U-03: DatePicker multi-instance → add regression test
- U-04: `apply_form_theme()` recursive walk → cache theme state
- U-05: `_bind_wheel_recursive()` O(n) → debounce + cache
- U-06: `ttk.Style` mutation per treeview → once per cycle
- U-07: Private `_views` across modules → add `get_view()`
- U-08: String-based tab dispatch → constants/enums
- U-09: 7-mixin MRO → document
- U-10: Redundant 3-layer refresh → consolidate
- U-11: Cancel edit state reset → verify

## 5. Database Layer
- DB-01: 40+ indexes → audit at 500+ client threshold
- DB-02: Verify schema_migrations tracking
- DB-03: Index redundancy audit

## 6. Testing
- T-01 through T-14: 14 test files to create
- T-15: Integration test generate→claim→verify
- T-16: Performance regression gate verification
- T-17: Flaky test check

## 7. CI/CD
- CI-01 through CI-08: Pipeline gaps

## 8. Documentation
- DOC-01 through DOC-06: Doc drift verification

## Subagent Delegation

| Agent | Parallel? | Tasks |
|-------|-----------|-------|
| `worker-api` | Yes | W-01..W-14, T-01..T-07, T-15, DOC-03, DOC-06 |
| `desktop-core` | Yes | D-01..D-12, DB-01..DB-06, C-01..C-04, T-08, T-09, T-12, T-14 |
| `ui-widgets` | Yes | U-01..U-03, T-12 |
| `ui-performance` | Yes | U-04..U-06, T-13 |
| `company-details` | After `ui-widgets` | U-09..U-11 |
| `cloudflare` | Yes | W-15, W-16, CI-06, CI-07 |
| `packaging-release` | Yes | W-07, CI-05, CI-08 |
| `qa-verifier` | Read-only | T-10, T-11, T-16, T-17 |

**Conflict:** `ui-widgets` and `company-details` both touch `widgets.py` → sequence.

## Verification Gates
- `ruff check .` → 0 errors
- `ruff format --check .` → 0 diffs
- `pytest tests/ -v --tb=short` → 100% pass
- `cd skyadmin-worker && npx tsc --noEmit` → 0 errors
- `cd skyadmin-worker && npm test` → 100% pass
- `python scripts/release_check.py` → RELEASE OK
