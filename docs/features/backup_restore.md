# Backup & Restore — Feature Detail

## Purpose
Manual + auto-backup (daily/weekly) with Fernet encryption, retention policy, restore with pool shutdown.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| Auto backup | `skyadmin_pro/services/auto_backup.py` | `should_run_backup()`, `auto_backups_dir()`, `retention_help_text()`, `AUTO_BACKUP_KEEP` |
| DB pool | `skyadmin_pro/db/core.py` | Pool shutdown before restore overwrite |
| Settings UI | `skyadmin_pro/ui/views/settings/backup_mixin.py` | `BackupMixin`, manual backup/restore UI |
| Config | `skyadmin_pro/config/tasks.py` | `SETTING_AUTO_BACKUP_*`, `SETTING_LAST_ENCRYPTED_BACKUP` |

## Architecture Decisions
- **Encrypted**: Fernet encryption on backup files (machine-bound).
- **Retention**: keeps newest 7 (`AUTO_BACKUP_KEEP`) encrypted backups; older deleted after each run.
- **Pool safety**: `db.shutdown()` called before restore overwrite to prevent WAL corruption.
- **Auto-backup UX** (Wave B F1.1): retention copy, Open AutoBackups folder, scheduler nudge + toast.

## Tests

| File | Covers |
|------|--------|
| `tests/test_auto_backup.py` | Auto-backup timing, retention |
| `tests/test_restore_backup_pool.py` | Pool shutdown before restore |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 7.4 | Background thread error surfacing | ✅ Landed |
| Wave B F1.1 | Scheduled auto-backup UX | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| Acceptable — no known issues | — | — |
