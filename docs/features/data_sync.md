# Data Sync — Feature Detail

## Purpose
Cross-device pull/push, LWW conflicts, encrypted credentials, HLC ordering, column allowlist.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| Desktop sync | `skyadmin_pro/services/data_sync.py` | `sync_data()`, `collect_local_changes()`, `apply_remote_changes()` |
| Sync schema | `skyadmin_pro/services/sync_schema.py` | `SYNC_TABLES`, `SYNC_ALLOWED_COLUMNS`, `SYNC_PUSH_ORDER` |
| Sync HLC | `skyadmin_pro/services/sync_hlc.py` | `hlc_now()`, `note_remote_hlc()`, `parse_hlc()` |
| License get | `skyadmin_pro/services/license/verify.py` | `find_license_file()`, `get_machine_id()` |
| Config | `skyadmin_pro/config/licensing.py` | `API_BASE_URL`, `SETTING_SYNC_*` |

## Worker Files

| File | Purpose |
|------|---------|
| `skyadmin-worker/src/routes/sync.ts` | Register, pull, push endpoints |
| `skyadmin-worker/src/sync_auth.ts` | Token hashing, TTL, `syncAuthMiddleware` |
| `skyadmin-worker/src/sync_eligibility.ts` | Ban/revoke/expiry checks on register |
| `skyadmin-worker/src/sync_push.ts` | Batch upsert, LWW conflict, `preparePushChanges` |
| `skyadmin-worker/src/sync_devices_schema.ts` | D1 `sync_devices` table with `expires_at` |
| `skyadmin-worker/src/sync_schema.ts` | Table/column definitions for worker |

## Data Flow
```
Desktop                              Worker
  collect_local_changes()
    → per-table rows with global_id
    → ensure_sync_ids() (assign HLC)
  sync_data() POST /api/sync/push
    → sync_push.ts: partitionPushChanges()
    → writePushBatch() (batch upsert)
    → LWW: compare updated_at; log conflicts
  GET /api/sync/pull
    → apply_remote_changes()
    → log_sync_conflicts() on LWW skip
  POST /api/sync/register
    → sync_eligibility: checkActivationEligibility()
    → reject banned/revoked/expired
    → upsertSyncDevice() with token_hash + TTL
```

## Architecture Decisions
- **Token hashed** (SHA-256) at rest; missing `expires_at` fails closed.
- **Column allowlist**: `SYNC_ALLOWED_COLUMNS` + `SYNC_EXCLUDED_COLUMNS` — `clients.group_id` numeric FK excluded (synced via `group_global_id`).
- **Batch push**: `writePushBatch()` replaces per-row SELECT (Phase 10.3 landed).
- **HLC ordering**: Hybrid Logical Clock for cross-device event ordering (migration m012).
- **Sync schema version**: `SYNC_SCHEMA_VERSION` in `sync_schema.py`.

## Tests

| File | Covers |
|------|--------|
| `tests/test_data_sync.py` | Pull/push, conflict log, credential encryption |
| `tests/test_sync_hlc.py` | HLC ordering |
| `skyadmin-worker/src/sync.test.ts` | Worker sync endpoints |
| `skyadmin-worker/src/sync_push.test.ts` | Batch push, LWW |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 8.1 | Harden sync register | ✅ Landed |
| Phase 8.3 | Encrypt `sync_device.json` | ✅ Landed |
| Phase 8.6 | Sync token rotation | ✅ Landed |
| Phase 10.3 | Batch sync push on Worker | ✅ Landed |
| Wave C C1 | Sync `client_groups` via `global_id` | ✅ Landed |
| Wave C C2 | Sync pull pagination UX | ✅ Landed |
| Wave C C3 | Conflict review UI | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| Legacy plaintext credential fallback | `data_sync.py:86–91` | P3 |
| SQL interpolation of LIMIT in sync pull | `routes/sync.ts:132` | P2 |
| Dynamic SQL string interpolation (trusted constants) | `data_sync.py:363–466` | P2 |
