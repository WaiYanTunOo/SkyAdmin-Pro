# Office Hub — Feature Detail

## Purpose
Contacts, vault (encrypted credentials), notebook, setup. Search debounce 300ms on all 4 search fields.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| View | `skyadmin_pro/ui/views/office_hub/view.py` | `OfficeHubView`, search debounce |
| Contacts | `skyadmin_pro/ui/views/office_hub/contacts_tab.py` | `ContactsTab` |
| Vault | `skyadmin_pro/ui/views/office_hub/vault_tab.py` | `VaultTab`, encrypted credentials |
| Notebook | `skyadmin_pro/ui/views/office_hub/notebook_tab.py` | `NotebookTab` |
| Setup | `skyadmin_pro/ui/views/office_hub/setup_tab.py` | `SetupTab` |
| Rollout | `skyadmin_pro/services/office_hub_rollout.py` | Rollout logic |
| DB mixins | `skyadmin_pro/db/office.py` | `office_contacts`, `office_credentials`, `notebook_entries` |
| Vault service | `skyadmin_pro/services/vault.py` | `encrypt_vault_secret()`, `decrypt_vault_secret()` |
| Config | `skyadmin_pro/config/office.py` | `CONTACT_CATEGORIES`, `OFFICE_SYSTEM_TYPES`, `VAULT_CATEGORIES` |
| Debounce | `ui/debounce.py` | 300ms shared utility |

## Architecture Decisions
- **Lazy tabs** (Phase 9.1): each tab panel built on first visit.
- **Debounce**: 300ms on 4 search fields via shared `ui/debounce.py`.
- **File splits** (Phase 9B): `contacts_tab.py`, `vault_tab.py`, `notebook_tab.py`, `setup_tab.py`.

## Tests

| File | Covers |
|------|--------|
| `tests/test_office_hub.py` | Layout, tab switching |
| `tests/test_office_hub_rollout.py` | Rollout logic |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 9.1 | Office Hub lazy tabs | ✅ Landed |
| Phase 9.4 | 300ms debounce on search fields | ✅ Landed |
| Phase 9B | File splits into tabs | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| 5 tabs historically in one file (~1100 lines) | `view.py` | ✅ Split done |
| No search debounce | `view.py` | ✅ 300ms landed |
