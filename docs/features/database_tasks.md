# Database & Tasks — Feature Detail

## Purpose
Core workspace: clients, tasks, suppliers, tax cycles, pipeline, renewals, courier tracking. Active-tab-only refresh prevents refresh storms.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| Tab container | `skyadmin_pro/ui/views/database_tasks/view.py` | `DatabaseTasksView`, `TAB_*` enum, `service_menu_panel_key()` |
| Constants | `skyadmin_pro/ui/views/database_tasks/constants.py` | `NONE_TASK` |
| Clients panel | `skyadmin_pro/ui/views/database_tasks/clients_panel.py` | `ClientsExpiryPanel` |
| Tasks panel | `skyadmin_pro/ui/views/database_tasks/task_panel.py` | `TaskPanel` |
| Suppliers panel | `skyadmin_pro/ui/views/database_tasks/suppliers_panel.py` | `SuppliersPanel` |
| Pipeline panel | `skyadmin_pro/ui/views/database_tasks/pipeline_panel.py` | `ServicePipelinePanel` |
| Renewal panel | `skyadmin_pro/ui/views/database_tasks/renewal_panel.py` | `RenewalPanel` |
| Courier panel | `skyadmin_pro/ui/views/database_tasks/courier_panel.py` | `CourierPanel` |
| Suppliers sub-pkg | `skyadmin_pro/ui/views/database_tasks/suppliers/panel.py` `directory_tab.py` `payments_tab.py` `services_tab.py` | Directory, AP payments, services tabs |
| DB mixins | `skyadmin_pro/db/clients.py`, `tasks.py`, `suppliers.py`, `courier.py`, `pipeline.py`, `financial.py` | Domain data access |
| Export | `skyadmin_pro/services/export.py` | `export_to_excel()` toolbar action |

## Architecture Decisions
- **Tab names** are module-level constants in `view.py` — never raw strings.
- **Lazy panels**: only built when tab selected (`_ensure_panel`).
- **Active-tab-only refresh** pauses hidden panels.
- **FTS5 search** in clients panel via `db/clients.py:search_clients()`.
- **Bulk client ops** (F1.3): multi-select → status/group/archive.

## Tests

| File | Covers |
|------|--------|
| `tests/test_database_tasks_refresh.py` | Active-tab refresh, lazy panels |
| `tests/test_clients_bulk_ops.py` | Multi-select batch operations |
| `tests/test_supplier_ap.py` | Supplier AP payments tab |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 9.1 | Lazy tab panel build | ✅ Landed |
| Phase 9C | Empty states on trees | ✅ Landed |
| Wave B F1.3 | Bulk client operations | ✅ Landed |
| Wave B F1.4 | Client grouping UX (`client_groups`) | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| `_fetch_all`/`_fetch_one` in wrong mixin | `db/clients.py:329–337` | P1 |
| String-based tab dispatch | `database_tasks/view.py` | P2 |
| `clients.group_id` numeric FK stays local (by design; groups sync via global_id) | `db/clients.py` | — |
