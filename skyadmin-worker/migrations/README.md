# D1 Migrations

Versioned SQL migrations for the Cloudflare D1 database.

## Usage

```bash
# Apply pending migrations to remote
npx wrangler d1 migrations apply skyadmin-db --remote

# Apply pending migrations to local dev DB
npx wrangler d1 migrations apply skyadmin-db --local
```

## Creating a New Migration

1. Create a file: `NNNN_description.sql` (e.g., `0002_add_pricing_overrides.sql`)
2. Write DDL statements (CREATE TABLE, ALTER TABLE, CREATE INDEX, etc.)
3. Run `npx wrangler d1 migrations apply skyadmin-db --remote`

## Naming Convention

- `0001_initial.sql` — baseline schema
- `0002_add_column.sql` — incremental changes
- Use zero-padded 4-digit numbers
- Use snake_case descriptions

## Notes

- Migrations are applied in filename order
- Each migration is applied exactly once (tracked by D1 internally)
- **Setup path:** always use `npx wrangler d1 migrations apply` (or `npm run db:migrate`)
- **Deprecated:** `schema.sql` via `wrangler d1 execute` / legacy `npm run db:init` — do not use for new or existing DBs
- `schema.sql` remains the full desired **end-state reference** only (token_hash + expires_at + audit)
- `0001_initial.sql` creates `sync_devices` with plaintext `token` (baseline)
- `0002_sync_devices_expires_at.sql` ALTERs legacy `sync_devices` tables that
  pre-date sync token TTL
- `0003_sync_tokens_hash.sql` rebuilds `sync_devices` with `token_hash` only
  (existing devices must re-register — D1 SQL cannot hash plaintext tokens)
- `0004_admin_audit_log.sql` adds `admin_audit_log`
- `0005_sync_devices_expires_backfill.sql` backfills `sync_devices.expires_at`
  for rows left NULL by the 0003 rebuild (no re-register required)
- `0006_sync_rows_hlc.sql` adds nullable `sync_rows.hlc` for Phase 2 HLC merge
  (request-path code falls back to `updated_at` ordering pre-migration)
