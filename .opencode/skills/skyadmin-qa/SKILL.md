---
name: skyadmin-qa
description: Use when running tests, verifying changes, or preparing for release. Runs pytest/vitest/release_check and reports pass/fail. Read-only verification role.
---

# SkyAdmin Pro — QA Skill

## Key Files

- `tests/` — 53 pytest test files
- `skyadmin-worker/src/*.test.ts` — 19 Vitest test files
- `tests/conftest.py` — Shared fixtures
- `pyproject.toml` — Pytest config (`[tool.pytest.ini_options]`)
- `skyadmin-worker/vitest.config.ts` — Vitest config
- `scripts/release_check.py` — Pre-ship release gate
- `.github/workflows/ci.yml` — CI pipeline
- `.github/workflows/release.yml` — Release pipeline
- `docs/UI_CHECKLIST.md` — Manual UI QA checklist
- `docs/MANUAL_QA.md` — Manual QA procedures

## Test Commands

### Python pytest
```bash
pytest tests/ -v --tb=short          # Full test suite
pytest tests/ -q --tb=short          # Quick run (release)
pytest tests/test_performance_clients.py  # Performance budget
pytest tests/test_performance_stress.py   # Stress tests
```

### Worker Vitest
```bash
cd skyadmin-worker && npm test       # Run all Vitest tests
cd skyadmin-worker && npx vitest run  # Same, explicit
```

### Release Check
```bash
python scripts/release_check.py     # Pre-ship QA gate
```

## Test Categories

### Unit Tests
- `test_crypto.py` — Encryption/decryption
- `test_db_mixins.py` — Database mixin operations
- `test_db_migrations.py` — Schema migrations
- `test_license_ed25519.py` — License signing/verification
- `test_secret_fields.py` — Encrypted field handling
- `test_vault.py` — Credential vault

### UI Tests
- `test_ui_smoke.py` — Basic UI creation
- `test_date_picker.py` — DatePickerField
- `test_form_widgets.py` — Form widgets
- `test_treeview_*.py` — Treeview components
- `test_visual_regression.py` — Visual consistency
- `test_display_scaling.py` — DPI scaling

### Integration Tests
- `test_phase4_walkthrough.py` — Full workflow walkthrough
- `test_company_details_refresh.py` — Company Details refresh
- `test_database_tasks_refresh.py` — Tab refresh behavior
- `test_dashboard_refresh.py` — Dashboard refresh

### Performance Tests
- `test_performance_clients.py` — Client query performance
- `test_performance_stress.py` — Stress testing
- `test_document_hub_polling.py` — Polling performance

### Security Tests
- `test_license_security.py` — License tamper detection
- `test_export_security.py` — Export redaction
- `test_secret_fields.py` — Field encryption

## QA Workflow

1. Run `pytest tests/ -v --tb=short` — all tests pass
2. Run `cd skyadmin-worker && npm test` — all Vitest tests pass
3. Run `python scripts/release_check.py` — RELEASE OK
4. Check `docs/UI_CHECKLIST.md` for manual UI verification
5. Verify no performance regressions in perf tests

## Conventions

- Read-only verification — do not edit source code
- Report pass/fail with specific failure details
- Run tests in parallel when possible
- Use `--tb=short` for concise error output
- Performance budget: tab switch < 100ms, data refresh < 500ms
