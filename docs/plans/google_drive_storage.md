# Plan: Local-first + multi-platform (Waves 0–4 foundation)

**Status:** Waves 0–4 foundation + Wave 2b / soft-delete (`SYNC_SCHEMA_VERSION` **7**) + Admin SKU generate + Drive backfill landed.

Canonical doc: [`docs/MULTI_PLATFORM.md`](../MULTI_PLATFORM.md) (includes web session + sync auth contract).

## Done
- D1 **0008** org-scoped sync + **0009** SKU flags (`web_enabled`, `drive_files_enabled`)
- Desktop auto sync + backup destination; auto-off when license `sync_enabled=0`
- `documents` + `financial_documents` in SYNC_TABLES with `drive_file_id` (desktop **m017**)
- Wave 2b tables (desktop **m018**) + soft-delete tombstones for sync product paths (schema **7**)
- Google Drive OAuth backend + Settings Connect (locked without `drive_files` SKU)
- Settings **Upload existing files to Drive** backfill (idempotent; skip if `drive_file_id` set)
- `POST /api/web/session` + sync gated on `sync_enabled`; Settings shows web entitlement line
- Admin UI + `POST /api/generate` set `org_id` / `sync_enabled` / `web_enabled` / `drive_files_enabled`

## Configure
- `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`
- Generate licenses with `org_id`, `web_enabled`, `drive_files_enabled` as needed (Admin form or API)

## Deferred
- Full web SPA (separate repo) — not started
- Stripe / Paddle billing — deferred
- `max_devices` column on `issued_licenses` — not in D1; add only with a migration when product needs it
- Do **not** blind-expand `SYNC_TABLES` or soft-delete into cascade-only / non-synced config tables
