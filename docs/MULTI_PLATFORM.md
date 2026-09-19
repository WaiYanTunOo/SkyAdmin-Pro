# Multi-platform SkyAdmin (Plane A / Plane B)

Sellable architecture: Windows and optional web share **org-scoped** row sync on Cloudflare (free tier). Heavy files use **each customer’s Google Drive**. Encrypted `.skybackup` is disaster recovery only.

## Landed status (2026-09-19)

| Area | Status |
|------|--------|
| Org-scoped sync (`org_id`, D1 **0008**) | Landed + deployed |
| SKU flags `sync` / `web` / `drive_files` (D1 **0009**) | Landed + deployed |
| Admin generate UI + `/api/generate` SKU fields | Landed (`org_id`, `sync_enabled`, `web_enabled`, `drive_files_enabled`, `max_devices`) |
| Desktop auto sync (interval + dirty push) | Landed |
| Drive OAuth foundation + Settings Connect | Landed (gated on `drive_files`) |
| Drive backfill (existing local → Drive) | Landed (Settings → Upload existing files) |
| `POST /api/web/session` | Landed (gated on `web`) |
| Wave 2a documents metadata + `drive_file_id` | Landed (`SYNC_SCHEMA_VERSION` 5 → **m017**) |
| Wave 2b web-surface tables | Landed (**m018**, schema **6**) |
| Soft-delete tombstones for sync product paths | Landed (`SYNC_SCHEMA_VERSION` **7**) |
| Conflict audit UX (winner/loser actors + org) | Landed (desktop **m019**) |
| Full web SPA UI | **Not started** (out of scope here) |
| Stripe billing | **Deferred** |
| `max_devices` on `issued_licenses` | Landed (D1 **0010**) — 0 = unlimited; default **1** |

`SYNC_SCHEMA_VERSION` **7** is locked on desktop (`skyadmin_pro/services/sync_schema`) and Worker (`skyadmin-worker/src/sync_schema.ts`) — same `SYNC_TABLES` list.

## SKUs (license entitlements)

| SKU | Entitlements | Behavior |
|-----|----------------|----------|
| Windows Solo | (none / local only) | One PC; local DB + files |
| Team Sync | `sync=1`, `org_id` shared | Multi-device HLC sync |
| Multi-platform | `sync=1`, `web=1` | + browser client |
| Files on Drive | `drive_files=1` | PDFs via customer Google OAuth |

Subscriptions use existing `expires_at`. Claims / generate body: `oid` / `org_id`, `sync` / `sync_enabled`, `web` / `web_enabled`, `drive_files` / `drive_files_enabled`, `max_devices` (0 = unlimited; default 1). Desktop Settings shows `Devices: N max` when capped; register returns **403** with `Device limit reached (n/max)` when the org is full.

Desktop Settings:

- Sync checkbox + auto-interval lock when Worker SKU has `sync_enabled=0` (pref + interval auto-off on register).
- Drive Connect / Prefer Drive / **Upload existing files to Drive** disabled without `drive_files`.
- License status line shows web entitlement (`Web access: included` / `not on this license`) and device cap when set (`Devices: 2 max`).
- Sync register **403** device-limit errors are shown in Settings feedback (Worker message passed through).

## Web API contract (external SPA author)

No full SPA ships in this repo. Browser clients call the Worker as below. **PDFs never go through the Worker** — only org-scoped row sync + license session.

### `POST /api/web/session`

Issue a short-lived browser session from an activation passcode. Requires license `web_enabled=1`.

**Request** (`Content-Type: application/json`):

```json
{ "code": "SKYPASS1:..." }
```

**Success `200`:**

```json
{
  "ok": true,
  "machine_id": "AABBCCDD11223344",
  "org_id": "firm:acme",
  "session_token": "<payload>.<hmac>",
  "expires_at": "2026-09-19T12:00:00.000Z"
}
```

- `session_token` — HMAC-signed claims `{ mid, org_id, exp }`; TTL **3600s**.
- Failures: `400` invalid/missing code; `403` banned/revoked/expired/`web` off; `503` signing secret missing.
- Rate limit: 10 / 60s per client key.

**Note:** The web session token authenticates the *browser identity* for a future SPA gate. **Row sync still uses the sync device token** (below), not this session JWT-like string.

### Sync auth (Plane A rows)

1. **`POST /api/sync/register`** with `{ "code": "<activation passcode>" }` — requires `sync_enabled=1`.
2. Response includes `sync_token`, `org_id`, `schema_version`, and SKU flags.
3. Subsequent **`POST /api/sync/pull`** / **`POST /api/sync/push`** require:
   - `Authorization: Bearer <sync_token>`
   - `X-Machine-Id: <16-hex machine id>`
4. Tokens are stored hashed (`token_hash`); plaintext is never in D1. TTL ~30 days with sliding refresh on use.
5. Org partition key is `(org_id, table_name, global_id)`. Solo licenses use `org_id = "m:" + machine_id`.

### Admin / sellable generate

`POST /api/generate` (Bearer `API_TOKEN` or admin cookie+CSRF) accepts optional:

| Field | Default | Notes |
|-------|---------|--------|
| `org_id` | `m:{mid}` | 1–64 chars `[A-Za-z0-9:_-]` |
| `sync_enabled` | `1` | 0/1 |
| `web_enabled` | `0` | 0/1 |
| `drive_files_enabled` | `0` | 0/1 |
| `max_devices` | `1` | 0 = unlimited; positive = seat cap |

Admin Generate form exposes the same fields. Response echoes them.

## Data planes

1. **Plane A (Worker/D1):** small JSON rows, key `(org_id, table_name, global_id)`, HLC last-write-wins.
2. **Plane B (customer Drive):** PDF bytes; rows store `drive_file_id` only (never upload bytes through Worker).

## Conflict rule

```
if no row → insert
else if remote.hlc > local.hlc → apply (update or tombstone)
else → keep local; audit loser
```

Legacy solo: `org_id = "m:" + machine_id` until admin assigns a shared org and folds silos.

## Auto sync

- Push ~1–2s after save (dirty queue).
- Pull every 30s in foreground (configurable 15/30/60 or off); immediate pull on focus/resume.
- Manual Sync remains.
- Auto sync is a no-op when user pref is off **or** license `sync_enabled=0`.

## Drive layout (customer account)

```text
SkyAdmin/Files/...
SkyAdmin/Backups/*.skybackup
```

## Vendor cost

- Cloudflare free for license + row sync (monitor quotas).
- Never store customer PDFs on vendor Drive.

## Table phases

- **2a:** core CRM + credentials + `documents` / `financial_documents` metadata + `drive_file_id` (`SYNC_SCHEMA_VERSION` 5, desktop **m017**).
- **2b (landed):** web-surface rows — `suppliers`, `pipeline_items`, `courier_logs`, `supplier_payments`, `supplier_services`, `client_months`, `renewal_items`, `tax_cycle_log`, `recurring_tasks` (desktop **m018**). Reminders stay on `tasks` (already synced). Filing statuses live on `clients`. Skipped: `settings`, `pricing_matrix`, `snippet_versions`, `checklist_templates` (config/blobs).
- **2b follow-up (`SYNC_SCHEMA_VERSION` 7):** soft-delete tombstones for suppliers / pipeline / courier (+ payments/services); `courier_logs.task_global_id` remap (numeric `task_id` still excluded). Soft-delete also covers `tasks`, `documents` / `financial_documents`, `client_credentials` / `office_credentials`, `clients` (cascade to synced children), `office_contacts`, `notebook_entries`, and `renewal_items` (list/get filter `deleted_at IS NULL`; sync collect includes tombstones). No further schema bump — wire format unchanged.

### Known limits

- Soft-deleted client names remain UNIQUE — `get_or_create_client` refuses the archived name (restore or pick another).
- Soft-deleted supplier names remain UNIQUE — `get_or_create_supplier` resurrects by name.
- `client_months` / `tax_cycle_log` / `recurring_tasks` are cascade-tombstoned with client delete; no dedicated single-row delete APIs yet.
- Cascade-only / non-synced config tables intentionally lack soft-delete — do not expand further unless a product path is broken.

See also: `docs/CRDT_DESIGN.md`, `docs/plans/google_drive_storage.md`.

## Google Drive OAuth setup (customer account)

PDFs stay in the **customer’s** Drive. The Worker never receives file bytes.

1. In Google Cloud Console create an OAuth **Desktop** client.
2. Set env vars (or Settings → store client id; secret is encrypted in SQLite):
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`
3. Redirect URI used by the app: `http://127.0.0.1:<ephemeral-port>/` (loopback).
4. License SKU must have `drive_files_enabled=1` (Worker generate / migration **0009**).
5. Settings → Data & backup → **Connect Google Drive**.
6. Optional: **Upload existing files to Drive** — backfills rows with empty `drive_file_id` (skips already linked).

Deploy note: D1 migrations **0008** then **0009** must be applied (`npm run db:migrate` in `skyadmin-worker`) before relying on SKU gates / web session.
