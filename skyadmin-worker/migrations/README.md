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
- The `schema.sql` file is kept for reference / legacy `db:init` usage
- For new databases, use `migrations apply` instead of `db:init`
- `0002_sync_devices_expires_at.sql` ALTERs legacy `sync_devices` tables that
  pre-date sync token TTL. Fresh installs get the column via 0002 (0001 creates
  the table without it). `schema.sql` remains the full desired end-state.
