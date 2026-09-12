# Company Details — Feature Detail

## Purpose
Per-company services, tax, VO/CSH, documents. 7-mixin lazy sub-tabs — forms usable without tree/scroll fight.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| Panel | `skyadmin_pro/ui/views/company_details/panel.py` | `CompanyDetailsPanel` (7 mixins) |
| Constants | `skyadmin_pro/ui/views/company_details/constants.py` | `SUBTAB_*`, `SUBTAB_NAMES` |
| General tab | `skyadmin_pro/ui/views/company_details/general_tab.py` | `GeneralTabMixin` |
| Accounting | `skyadmin_pro/ui/views/company_details/accounting_setup_tab.py` | `AccountingSetupTabMixin` |
| Tax IDs | `skyadmin_pro/ui/views/company_details/tax_ids_tab.py` | `TaxIdsTabMixin` |
| Filing | `skyadmin_pro/ui/views/company_details/filing_tab.py` | `FilingTabMixin` |
| VO/CSH Setup | `skyadmin_pro/ui/views/company_details/vo_csh_setup_tab.py` | `VoCshSetupTabMixin` |
| VO & CSH | `skyadmin_pro/ui/views/company_details/vo_csh_tab.py` | `VoCshTabMixin` |
| Financial Docs | `skyadmin_pro/ui/views/company_details/financial_docs_tab.py` | `FinancialDocsTabMixin` |
| Rollout | `skyadmin_pro/services/tax_ids_rollout.py`, `vo_csh_rollout.py` | Single/multi-client inference |

## Architecture Decisions
- **MRO**: mixins searched left→right: General → Accounting → Tax IDs → Filing → VO/CSH Setup → VO & CSH → Financial Docs → CTkFrame.
- **Trees outside CanvasScrollFrame** — split-pane tabs (Tax IDs, Filing) keep trees fixed outside form scroll frames; General tab cards scroll smoothly inside `CanvasScrollFrame` with mousewheel fallback from `ThemedTreeview`.
- **Placeholder & Activation Safety** — `__empty__` placeholder rows filter to `None` in `selected_iid()`, preventing `ValueError` / `TypeError` on click, keyboard activation (`<Return>`/`<Space>`), and action buttons.
- **Cancel Edit Controls** — General tab Service and Document forms include explicit Cancel buttons and automatically clear edit state on sub-tab or company changes.
- **Lazy sub-tabs**: only built on first visit.
- **Refresh dispatch** lives on panel class, not mixins (avoids override conflicts).
- Sub-tab names in `constants.py` — imported by `database_tasks/view.py` to avoid circular imports.

## Tests

| File | Covers |
|------|--------|
| `tests/test_general_tab_complete.py` | Complete General tab functions, date validation, cancel edit, shortcut routing, wheel delegation |
| `tests/test_company_details_refresh.py` | Sub-tab refresh, lazy build |
| `tests/test_tax_ids_rollout.py` | Tax ID field inference rollout |
| `tests/test_vo_csh_rollout.py` | VO/CSH inference (clear copy of vo_csh_rollout.py surface) |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 9B | Split into per-tab files | ✅ Landed |
| U1.0a | Trees outside CanvasScrollFrame | ✅ Landed |
| Wave B F1.5 | Audit log surfaces (tax cycle + sync conflicts) | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| 7-mixin MRO complexity | `panel.py:57–74` | P1 |
| Redundant 3-layer refresh dispatch | `panel.py:244–302` | P1 |
| Private `_views` access (cross-module) | `panel.py:930–932` | P2 |
| String-based tab dispatch | `panel.py` + `database_tasks/view.py` | P2 |
| `vo_csh_rollout.py` duplicated inference | `services/vo_csh_rollout.py:77–116` | P2 |
