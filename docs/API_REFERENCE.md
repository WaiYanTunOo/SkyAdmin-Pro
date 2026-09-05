# Worker API Reference

Base URL: `https://<your-worker>.workers.dev`

## Authentication

All protected endpoints require `Authorization: Bearer <API_TOKEN>` header.

## Public Endpoints

### GET /api/ping

Health check.

**Response:** `200 OK`
```json
{ "ok": true, "service": "skyadmin-api", "ts": "2026-01-01T00:00:00.000Z" }
```

### GET /api/control

Returns the control list (latest version, update URL, ban list, revocations).

**Response:** `200 OK`
```json
{
  "ok": true,
  "version": 42,
  "update": { "version": "0.3.2", "url": "https://..." },
  "bans": ["AABBCCDD11223344"],
  "revocations": ["nonce1", "nonce2"]
}
```

### POST /api/claim

Public activation burn. No auth required.

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

Register a device for sync. Returns a sync token.

**Request:**
```json
{ "machine_id": "AABBCCDD11223344", "device_name": "My Phone" }
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

Returns the latest published app version.

## Protected Endpoints

Require `Authorization: Bearer <API_TOKEN>`.

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

### POST /api/sync/push

Push local changes to the server.

### GET /api/sync/pull

Pull server changes since last sync.

### GET /api/sync/schema

Returns the D1 schema for client-side migration.

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
