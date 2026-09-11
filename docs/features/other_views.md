# Other Views — Feature Detail

## Purpose
Supporting views: global search, audit log, export filter, utilities view, base view chrome.

## Code Files

| View | File | Purpose |
|------|------|---------|
| Base view | `skyadmin_pro/ui/views/base.py` | `BaseView` — shared page header + body chrome |
| Global search | `skyadmin_pro/ui/views/global_search.py` | Cross-entity find |
| Audit log | `skyadmin_pro/ui/views/audit_log.py` | Desktop audit viewer (tax_cycle_log, sync_conflicts) |
| Export filter | `skyadmin_pro/ui/views/export_filter_dialog.py` | Export column filter dialog |
| Utilities view | `skyadmin_pro/ui/views/utilities.py` | Utility tools entry from sidebar |

## Architecture Decisions
- **BaseView**: every sidebar destination extends it; provides title header, subtitle, body frame, `on_show()`/`on_hide()` lifecycle hooks.
- **Global search**: cross-entity search across clients, tasks, contacts, notebook.
- **Audit log**: entry from Settings; Wave B F1.5 returns tax cycle + sync conflicts.
- **Lazy loading**: all views instantiated on first visit by `main_window._ensure_view`.

## Tests

| File | Covers |
|------|--------|
| `tests/test_audit_log.py` | Audit log viewer |
| `tests/test_phase4_walkthrough.py` | Per-view walkthrough |
| `tests/test_visual_regression.py` | Visual regression |
| `tests/test_ui_smoke.py` | UI smoke tests |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Wave B F1.5 | Audit log viewer | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| Acceptable — no known issues | — | — |
