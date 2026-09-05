# Worker API Reference

Base URL: `https://<your-worker>.workers.dev`

## Authentication

Protected **JSON API** routes accept either:

1. `Authorization: Bearer <API_TOKEN>`, or
2. Same-origin admin session cookie **plus** `X-CSRF-Token` on mutating requests (`auth.ts`)

Admin **HTML** pages use the session cookie only (login CSRF on the form). Do not document the API as Bearer-only — see `docs/WORKER_ADMIN.md`.

Public endpoints (`/api/ping`, `/api/control`, `/api/claim`, `/api/sync/register`, pricing GET, signing public key) do not require Bearer auth; several are rate-limited.

## Public Endpoints

### GET /api/ping

Health check.

**Response:** `200 OK`
```json
{ "ok": true, "service": "skyadmin-api", "ts": "2026-01-01T00:00:00.000Z" }
```

### GET /api/control

Returns a **SKYCTRL2-signed `text/plain` envelope** (not JSON). Rate-limited (~30/min per IP).

**Response:** `200 OK` with `Content-Type: text/plain; charset=utf-8`

Body is a signed control list (revocations, bans, used nonces, optional `LATEST version url`). Clients verify via Ed25519; see desktop license/control consumers.

### POST /api/claim

Public activation burn. No auth required. Rate-limited.

**Request:**
```json
{ "code": "<activation-code>" }
```

**Response:** `200 OK`
```json
{
  "ok": true,
  "message": "Activation claimed for machine AABBCCDD11223344.",
  "nonce": "...",
  "already_used": false,
  "license_key": "...",
  "expires_at": "2026-02-01T00:00:00Z"
}
```

### POST /api/sync/register

Exchange a valid activation code for a device sync token. Rejects banned/revoked/**expired** licenses (403). Rate-limited. After D1 migration `0003_sync_tokens_hash`, devices must re-register (tokens stored as SHA-256 hashes).

**Request:**
```json
{ "code": "<activation-code>" }
```

**Response:** `200 OK`
```json
{
  "ok": true,
  "machine_id": "AABBCCDD11223344",
  "sync_token": "...",
  "schema_version": 1
}
```

### GET /api/signing/public-key

Returns the Worker's Ed25519 public key for verification.

### GET /api/pricing

Returns activation pricing packages.

**Response:** `200 OK`
```json
{
  "ok": true,
  "packages": [
    { "label": "7 Days", "days": 7, "price_thb": 500 }
  ],
  "over_year_text": "Over 1 Year — discuss on WhatsApp"
}
```

### GET /api/update

Returns the latest published app version (installer URL when published via release pipeline).

## Protected Endpoints

Require Bearer token **or** same-origin session cookie + CSRF (see Authentication).

### POST /api/generate

Generate a signed license key.

**Request:**
```json
{ "mid": "AABBCCDD11223344", "days": 30 }
```

**Response:** `200 OK`
```json
{
  "ok": true,
  "license_key": "...",
  "passcode": "SKYPASS1:...",
  "nonce": "...",
  "expires_at": "2026-02-01T00:00:00Z"
}
```

### POST /api/revoke

Revoke a license nonce.

**Request:** `{ "nonce": "..." }`

### POST /api/unrevoke

Un-revoke a license nonce.

**Request:** `{ "nonce": "..." }`

### POST /api/ban

Ban a machine ID.

**Request:** `{ "mid": "AABBCCDD11223344", "reason": "fraud" }`

### POST /api/unban

Un-ban a machine ID.

**Request:** `{ "mid": "AABBCCDD11223344" }`

### GET /api/bans

List all banned machine IDs.

### GET /api/records

List issued licenses with pagination.

**Query params:** `page` (default 1), `limit` (default 50, max 500)

### POST /api/used

Mark a nonce as used.

### POST /api/revoke-pc

Revoke by passcode.

### POST /api/pricing

Update pricing packages (admin only).

**Request:**
```json
{
  "packages": [{ "label": "7 Days", "days": 7, "price_thb": 500 }],
  "over_year_text": "Custom message"
}
```

### POST /api/update

Publish a new app version.

**Request:** `{ "version": "0.3.2", "url": "https://..." }`

### POST /api/purge-licenses

Archive old license records.

**Request:** `{ "older_than_days": 30 }`

## Sync Endpoints

Device sync uses `Authorization: Bearer <sync_token>` and `X-Machine-Id` (not the owner `API_TOKEN`). Tokens are stored hashed; null/missing `expires_at` is rejected. Pull and push are rate-limited (~30/min per IP).

### POST /api/sync/push

Push local changes to the server.

### GET /api/sync/pull

Pull server changes since last sync. Rate-limited.

### GET /api/sync/schema

Returns the sync table allowlist / schema version for clients.

**Note:** `client_groups` syncs as its own table (`SYNC_SCHEMA_VERSION` 2+). Numeric `clients.group_id` is never uploaded; membership uses `group_global_id` remapped locally.

## Admin Endpoints

### GET /{ADMIN_PATH}/

Admin dashboard (requires session cookie).

### POST /{ADMIN_PATH}/login

Login with password. Sets session cookie on success.

### POST /{ADMIN_PATH}/logout

Clears session cookie.

## Viewer Endpoints

### GET /viewer

PWA viewer shell (read-only mobile access).

### GET /viewer/manifest.webmanifest

PWA manifest.

### GET /viewer/sw.js

Service worker for offline caching.
