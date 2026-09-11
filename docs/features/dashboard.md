# Dashboard — Feature Detail

## Purpose
Stat cards, next actions, expiry alerts, overdue payments, pending tasks, client month closes — the default view loaded at startup.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| UI view | `skyadmin_pro/ui/views/dashboard.py` | `DashboardView`, `snap_fingerprint` |
| DB query | `skyadmin_pro/db/tax.py` | `dashboard_snapshot()` |
| Tracking | `skyadmin_pro/services/tracking.py` | `classify_expiry()`, `days_until()`, `effective_expiry_date()`, `expiry_label()` |
| Snippets | `skyadmin_pro/services/snippets.py` | `effective_text()`, `load_snippet_overrides()` |
| Workflow | `skyadmin_pro/services/workflow.py` | `copy_to_clipboard()`, `format_eod_report()`, `create_client_workspace()` |
| Config | `skyadmin_pro/config/services.py` | `SERVICE_TYPES`, `TAX_FILING_FIELDS`, `EXPIRY_WATCH_TYPES` |
| UI shell | `skyadmin_pro/ui/main_window.py` | View registration (dashboard loaded first) |

## Data Flow
```
Database.savepoint() → db.tax.dashboard_snapshot()
    → counts (clients, expiring, overdue, pending)
    → detail trees (expiry, pending, overdue, suppliers, ongoing, reports, tax overview)
DashboardView refreshes only when data fingerprint changes.
Progressive trees staged on on_show() → after(100) → sub-tab click.
```

## Architecture Decisions
- **First paint**: stat cards render immediately; detail trees staged progressively.
- **Fingerprint**: `snap_fingerprint()` compares counts + IDs; skips tree rebuild when unchanged.
- **Refresh budget**: `dashboard_snapshot()` uses a single connection, ≤40 statements (target: ≤3 round-trips).
- **Lazy**: only view loaded at startup by `main_window._ensure_view`.

## Tests

| File | Covers |
|------|--------|
| `tests/test_dashboard_layout.py` | Stat card layout, tree placement |
| `tests/test_dashboard_paint.py` | First-paint timing (`SKYADMIN_DASHBOARD_PAINT=1`) |
| `tests/test_dashboard_refresh.py` | Refresh budget, fingerprint skip, query count |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 7.2 | Dashboard query budget (snapshot) | ⚠️ Partial — ≤40 stmts/1 conn; full ≤3 SQL deferred |
| Phase 9.3 | Progressive detail trees on `on_show` | ✅ Landed |
| Wave A F1.6 | Dashboard Export PDF + tax overview | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| First paint still heavy — defer more of `build()` cost | `dashboard.py:build()` | P0 |
| Fingerprint only counts (stale data detection gap) | `dashboard.py:50–87` | P1 |
| `dashboard_snapshot()` 12+ connections on slow disks | `db/tax.py:dashboard_snapshot()` | P0 |
| Private `_views` accessed from dashboard | `dashboard.py:1092` | P2 |
