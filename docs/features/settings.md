# Settings — Feature Detail

## Purpose
Appearance, license card, business defaults, checklist/pricing, backup, workspace paths. General eager, others lazy.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| View | `skyadmin_pro/ui/views/settings/view.py` | `SettingsView`, `_ensure_panel()`, lazy tab loading |
| License mixin | `skyadmin_pro/ui/views/settings/license_mixin.py` | `LicenseMixin`, license card, sync controls |
| Pricing mixin | `skyadmin_pro/ui/views/settings/pricing_mixin.py` | `PricingMixin`, pricing matrix CRUD |
| Backup mixin | `skyadmin_pro/ui/views/settings/backup_mixin.py` | `BackupMixin`, manual/encrypted backup, restore |
| Checklist mixin | `skyadmin_pro/ui/views/settings/checklist_mixin.py` | `ChecklistMixin`, renewal template editor |
| Workspace mixin | `skyadmin_pro/ui/views/settings/workspace_mixin.py` | `WorkspaceMixin`, folder paths, portal URL |
| Sync conflicts | `skyadmin_pro/ui/views/settings/sync_conflicts_dialog.py` | Conflict viewer dialog |
| Config | `skyadmin_pro/config/licensing.py` | `API_BASE_URL`, `REVOCATION_URL`, sync settings |
| Config | `skyadmin_pro/config/workspace.py` | `DEFAULT_PORTAL_URL`, folder constants |

## Architecture Decisions
- **Lazy tabs**: General is eager (built on first open); License, Business, Data & backup built on first visit.
- **Checklist scroll**: single scroll surface (no nested CTkScrollableFrame) — Phase 9B landed.
- **Integrity banner**: shows `quick_check()` failure on open — Phase 7.3 landed.
- **File splits** (Phase 9B): 5 mixins extracted from monolithic `settings.py`.

## Tests

| File | Covers |
|------|--------|
| `tests/test_settings_lazy_tabs.py` | Lazy tab loading on first visit |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 7.3 | Integrity banner on open | ✅ Landed |
| Phase 9B | Split into package | ✅ Landed |
| Phase 9C | Sync/loading states | ✅ Landed |
| Phase 9C | Filing history save debounce 300ms | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| Nested checklist scroll (historical) | `view.py` | ✅ Removed |
| Sync conflicts dialog in settings | `sync_conflicts_dialog.py` | — |
