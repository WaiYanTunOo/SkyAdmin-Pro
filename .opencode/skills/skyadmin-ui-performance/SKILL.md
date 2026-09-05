---
name: skyadmin-ui-performance
description: Use when fixing scroll jank, tab refresh storms, lazy loading, or polling issues. Handles active-tab-only refresh, pausing hidden polling, and reducing nested CTkScrollableFrame.
---

# SkyAdmin Pro — UI Performance Skill

## Key Files

- `skyadmin_pro/ui/views/database_tasks/view.py` — Tab view with 8 panels
- `skyadmin_pro/ui/views/dashboard.py` — Dashboard refresh budget
- `skyadmin_pro/ui/views/document_hub.py` — Polling, tool panels
- `skyadmin_pro/ui/views/company_details/panel.py` — Company Details sub-tabs
- `skyadmin_pro/ui/main_window.py` — View swapping, sidebar nav
- `skyadmin_pro/ui/canvas_scroll.py` — Scroll architecture
- `skyadmin_pro/ui/async_ui.py` — Async UI helpers
- `tests/test_database_tasks_refresh.py` — Refresh tests
- `tests/test_dashboard_refresh.py` — Dashboard refresh tests
- `tests/test_document_hub_polling.py` — Polling tests
- `tests/test_performance_clients.py` — Performance budget tests
- `tests/test_performance_stress.py` — Stress tests

## Known Issues

1. **Tab refresh storms** — Switching tabs refreshes all 8 panels instead of just the active one.
2. **Scroll jank** — Nested `CTkScrollableFrame` causes performance issues.
3. **Hidden polling** — Background tabs continue polling, wasting resources.
4. **Dashboard/Document Hub** — Need lazy load and polling pause.

## Architecture

### Active-Tab-Only Refresh

When switching between tabs in `database_tasks/view.py`:
- Only the newly active tab should refresh its data
- Other tabs should stop their refresh timers
- Use a flag or callback to track which tab is active

### Lazy Loading

Views should be lazy-loaded:
- `main_window.py` only instantiates views on first access
- Sub-tabs in `company_details/panel.py` should build on first visit
- Dashboard should defer expensive operations until visible

### Polling Management

Document Hub has polling for file changes:
- Pause polling when tab is not visible
- Resume polling when tab becomes active
- Use `after_cancel()` to stop pending poll calls

### Scroll Architecture

Minimize nesting of `CTkScrollableFrame`:
- Use `CTkFrame` with manual scrollbar when possible
- Flatten scroll hierarchy where content allows
- Consider virtual scrolling for large lists

## Conventions

- Use `after()` for delayed refresh, `after_cancel()` to cancel
- Track active tab via sidebar selection callback
- Performance budget: tab switch < 100ms, data refresh < 500ms
- Profile with `time.perf_counter()` for performance-critical paths
