# Utilities — Feature Detail

## Purpose
Support services: file ops, workflow, undo, column state, process jobs, remote pricing, data hygiene, tax calendar, tracking, network, storage.

## Code Files

| Feature | File | Key symbols |
|---------|------|-------------|
| File ops | `skyadmin_pro/services/file_ops.py` | `open_in_file_manager()`, `copy_file()`, `sanitize_amount()`, `format_thousands()`, `parse_flexible_date()` |
| Workflow | `skyadmin_pro/services/workflow.py` | `copy_to_clipboard()`, `create_client_workspace()`, `format_eod_report()` |
| Undo | `skyadmin_pro/services/undo_manager.py` | `UndoManager` |
| Column state | `skyadmin_pro/services/column_state.py` | `column_visibility` helpers |
| Process jobs | `skyadmin_pro/services/process_jobs.py` | Background job runner, thread error surfacing |
| Remote pricing | `skyadmin_pro/services/remote_pricing.py` | Fetch pricing from Worker |
| Data hygiene | `skyadmin_pro/services/data_hygiene.py` | Data cleanup routines |
| Tax calendar | `skyadmin_pro/services/tax_calendar.py` | Monthly tax SOP, filing tracking |
| Tracking | `skyadmin_pro/services/tracking.py` | `classify_expiry()`, `days_until()`, `effective_expiry_date()` |
| Net | `skyadmin_pro/services/net.py` | Network utilities |
| Storage | `skyadmin_pro/services/storage_backend.py` | Storage abstraction |
| Client cmds | `skyadmin_pro/services/client_commands.py` | Client command helpers |

## Tests

| File | Covers |
|------|--------|
| `tests/test_file_ops.py` | Sanitize, merge, archive |
| `tests/test_workflow.py` | Clipboard, workspace creation |
| `tests/test_undo.py` | Undo/redo |
| `tests/test_column_state.py` | Column visibility persistence |
| `tests/test_process_jobs.py` | Background jobs |
| `tests/test_remote_pricing.py` | Remote pricing fetch |
| `tests/test_data_hygiene.py` | Data cleanup |
| `tests/test_net.py` | Network utilities |
| `tests/test_storage_backend.py` | Storage abstraction |
| `tests/test_workspace_paths.py` | Workspace path resolution |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| `list_service_types()` cache not invalidated externally | `db/clients.py:234` | P3 |
| `subprocess.Popen` with user-influenced paths | `services/file_ops.py:196–198` | P1 |
