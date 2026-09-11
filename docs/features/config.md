# Config — Feature Detail

## Purpose
Application constants, default settings, UI copy — 8 domain modules re-exported from package init.

## Code Files

| Layer | File | Contains |
|-------|------|----------|
| Package | `skyadmin_pro/config/__init__.py` | `APP_NAME`, `APP_VERSION`, re-exports, checklist templates |
| Nav | `skyadmin_pro/config/nav.py` | `NAV_ITEMS`, `NAV_*` sidebar destinations |
| Documents | `skyadmin_pro/config/documents.py` | `FINANCIAL_DOC_CATEGORIES`, `FINANCIAL_DOC_FOLDER_MAP`, `IMAGE_SUFFIXES`, `PDF_SUFFIX` |
| Licensing | `skyadmin_pro/config/licensing.py` | `API_BASE_URL`, `REVOCATION_URL`, `LEGAL_*`, `MOBILE_VIEWER_URL`, `PRICING_TIERS` |
| Office | `skyadmin_pro/config/office.py` | `CONTACT_CATEGORIES`, `NOTEBOOK_ENTRY_TYPES`, `VAULT_CATEGORIES`, `OWNER_*` |
| Pricing | `skyadmin_pro/config/pricing.py` | `PRICING_*`, `DEFAULT_CHARGE_LINES`, pricing helpers |
| Services | `skyadmin_pro/config/services.py` | `SERVICE_TYPES`, `TAX_FILING_FIELDS`, `DOCUMENT_TYPES` |
| Tasks | `skyadmin_pro/config/tasks.py` | `PIPELINE_STEPS`, `TASK_CATEGORIES`, setting keys |
| Workspace | `skyadmin_pro/config/workspace.py` | `FOLDER_*`, `SETTING_PORTAL_URL`, `SETTING_WORKSPACE_*` |

## Architecture Decisions
- **Single version source**: `APP_VERSION` reads `pyproject.toml` (Phase 7.5 landed).
- **Re-exports**: `config/__init__.py` re-exports every public name so `from skyadmin_pro.config import X` works.
- **Checklist data**: renewal checklist templates live in `config/__init__.py` (spans domains).

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| `config/__init__.py` ~300 lines monolith, checklist data embedded | `config/__init__.py:189–301` | P1 |
| XOR obfuscation in config values | `config/__init__.py:122–322` | P3 (acceptable) |
