# Cloudflare Worker — Feature Detail

## Purpose
Cloudflare Worker backend: license generation/claim, sync API, control list, admin UI, viewer PWA, pricing, update, D1 database.

## Code Files

### Router & Core

| Layer | File | Key symbols |
|-------|------|-------------|
| Router | `skyadmin-worker/src/index.ts` | Hono app, all route wiring |
| DB | `skyadmin-worker/src/db.ts` | `Env` type, D1 bindings |
| Env | `skyadmin-worker/src/env_secrets.ts` | Secret management |
| Auth | `skyadmin-worker/src/auth.ts` | `authMiddleware`, timing-safe, fail-closed |
| CORS | `skyadmin-worker/src/cors.ts` | `corsMiddleware` |
| CSP | `skyadmin-worker/src/csp.ts` | CSP headers |
| Signing | `skyadmin-worker/src/signing.ts` | Ed25519 key handling |
| Verification | `skyadmin-worker/src/verification.ts` | License verification |
| Rate limit | `skyadmin-worker/src/rate_limit.ts` | `checkRateLimit()`, `purgeStaleRateLimits()` |
| Timing-safe | `skyadmin-worker/src/timing_safe.ts` | Constant-time compare |
| Admin security | `skyadmin-worker/src/admin_security.ts` | Admin auth hardening |

### Routes

| Route | File | Endpoint |
|-------|------|----------|
| Generate | `routes/generate.ts` | `POST /api/generate` |
| Claim | `routes/claim.ts` | `POST /api/claim` |
| Revoke | `routes/revoke.ts` | `POST /api/revoke`, `POST /api/unrevoke` |
| Ban | `routes/ban.ts` | `POST /api/ban`, `POST /api/unban`, `GET /api/bans` |
| Used | `routes/used.ts` | `GET /api/used`, `POST /api/revoke-pc` |
| Records | `routes/records.ts` | `GET /api/records`, `GET /api/records/:machine` |
| Control | `routes/control.ts` | `GET /api/control` |
| Sync | `routes/sync.ts` | `POST /api/sync/register`, `GET /api/sync/pull`, `POST /api/sync/push`, `GET /api/sync/schema` |
| Pricing | `routes/pricing.ts` | `GET /api/pricing`, `POST /api/pricing` |
| Update | `routes/update.ts` | `GET /api/update`, `POST /api/update` |
| Purge | `routes/purge.ts` | `POST /api/purge` |
| Viewer | `routes/viewer.ts` | PWA viewer HTML + service worker |
| Signing info | `routes/signing_info.ts` | `GET /api/signing/public-key` |

### Admin

| File | Purpose |
|------|---------|
| `routes/admin/index.ts` | Admin route wiring |
| `routes/admin/handler.ts` | Admin handlers, login, rate limit |
| `routes/admin/session.ts` | Session management, CSRF |
| `routes/admin/pages.ts` | Admin HTML/JS pages |

### Sync Core

| File | Purpose |
|------|---------|
| `sync_auth.ts` | Token hash, TTL, `syncAuthMiddleware` |
| `sync_eligibility.ts` | Ban/revoke/expiry checks |
| `sync_push.ts` | Batch upsert, LWW conflict |
| `sync_devices_schema.ts` | D1 sync_devices table |
| `sync_schema.ts` | Table/column definitions |

### License Core

| File | Purpose |
|------|---------|
| `license_policy.ts` | License policy enforcement |
| `license_status.ts` | Status checks |
| `packages.ts` | Package definitions |

### D1 Migrations

| File | Purpose |
|------|---------|
| `migrations/0001_initial.sql` | Initial schema |
| `migrations/0002_sync_devices_expires_at.sql` | Sync device TTL |
| `migrations/0003_sync_tokens_hash.sql` | Token hashing |
| `migrations/0004_admin_audit_log.sql` | Admin audit trail |
| `migrations/0005_sync_devices_expires_backfill.sql` | Backfill expiry |
| `migrations/0006_sync_rows_hlc.sql` | HLC column for sync rows |
| `migrations/0007_drop_redundant_sync_devices_index.sql` | Index cleanup |
| `schema.sql` | End-state reference (do not db:init) |

## Tests

| File | Covers |
|------|--------|
| `auth.test.ts` | Timing-safe auth |
| `cors.test.ts` | CORS behavior |
| `rate_limit.test.ts` | Rate limiting |
| `signing.test.ts` | Signing operations |
| `verification.test.ts` | License verification |
| `license_policy.test.ts` | Policy enforcement |
| `license_status.test.ts` | Status checks |
| `packages.test.ts` | Package definitions |
| `sync.test.ts` | Sync endpoints |
| `sync_push.test.ts` | Batch push |
| `claim.test.ts` | Claim endpoint |
| `control.test.ts` | Control list |
| `handlers.test.ts` | Admin/records handlers |
| `admin.test.ts` | Admin session flow |
| `viewer.test.ts` | PWA viewer |
| `update.test.ts` | Update endpoint |
| `purge.test.ts` | Purge endpoint |
| `integration.test.ts` | Full lifecycle |
| `integration_security.test.ts` | Security integration |
| `lifecycle.test.ts` | License lifecycle |
| `migrations.test.ts` | Migration runner |

## Architecture Decisions
- **Hono framework**: lightweight, TypeScript strict mode.
- **D1 SQLite**: edge database for licenses, sync rows, audit.
- **Fail-closed auth**: `crypto.subtle` unavailable → reject, not `===` comparison.
- **Rate limiting**: persistent D1 `rate_limits` table; claim/register/push/pull/control + admin writes.
- **CSP**: all HTML responses have `default-src 'none'` + script nonce.
- **Sync tokens**: hashed at rest, TTL 30 days, rotation on renewal.

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 8.1 | Sync register hardening | ✅ Landed |
| Phase 8.2 | Route tests | ✅ Landed |
| Phase 8.5 | CORS review | ✅ Landed |
| Phase 10.3 | Batch sync push | ✅ Landed |
| S1 | Timing-safe, TTL, CSP, rate limits | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| `recordsHandler` full table scan of revocations + used_nonces | `routes/records.ts:24–29` | P1 |
| Hardcoded LIMIT 2000 in `summarizeMachines` | `routes/records.ts:54–55` | P3 |
| Dynamic `import()` in hot path | `routes/generate.ts:25–27` | P2 |
| D1 query error handling in most routes | `routes/generate.ts:53–55` | P2 |
