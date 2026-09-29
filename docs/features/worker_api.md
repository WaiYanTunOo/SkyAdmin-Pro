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
| Generate | `routes/generate.ts` + `generate_insert.ts` + `generate_flags.ts` | `POST /api/generate` |
| Claim | `routes/claim/index.ts` (handler/validate/lookup/apply/iat) | `POST /api/claim` |
| Revoke | `routes/revoke.ts` + `handlers/revoke.ts` | `POST /api/revoke`, `POST /api/unrevoke` |
| Ban | `routes/ban.ts` + `handlers/ban.ts` | `POST /api/ban`, `POST /api/unban`, `GET /api/bans` |
| Used | `routes/used.ts` | `GET /api/used`, `POST /api/revoke-pc` |
| Records | `routes/records/index.ts` (handler/enrich/query/summary) | `GET /api/records`, `GET /api/records/:machine` |
| Control | `routes/control.ts` | `GET /api/control` |
| Sync | `routes/sync/index.ts` (register/pull/push/schema) | `POST /api/sync/register`, `GET /api/sync/pull`, `POST /api/sync/push`, `GET /api/sync/schema` |
| Pricing | `routes/pricing.ts` + `pricing_parts/` | `GET /api/pricing`, `POST /api/pricing` |
| Update | `routes/update.ts` | `GET /api/update`, `POST /api/update` |
| Purge | `routes/purge/index.ts` (handler/chunk/select/write) | `POST /api/purge` |
| Viewer | `routes/viewer/index.ts` (handler/manifest/sw + parts) | PWA viewer HTML + service worker |
| Signing info | `routes/signing_info.ts` | `GET /api/signing/public-key` |

### Admin

| File | Purpose |
|------|---------|
| `routes/admin/index.ts` | Admin route wiring |
| `routes/admin/handler/` (gate, login, logout, login_html) | Admin handlers, login, rate limit |
| `routes/admin/session/` (cookie, csrf, tokens, attempts, epoch) | Session management, CSRF |
| `routes/admin/pages.ts` + `routes/admin/parts/` | Admin HTML/JS pages (css, html, js_0–7) |

### Sync Core

| File | Purpose |
|------|---------|
| `sync_auth.ts` | Token hash, TTL, `syncAuthMiddleware` |
| `sync_eligibility.ts` | Ban/revoke/expiry checks |
| `sync_push/` | Batch upsert, LWW conflict (`partitionPushChanges`) |
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
| `migrations/0008_org_scoped_sync.sql` | Multi-platform org-scoped sync |
| `migrations/0009_sku_entitlements.sql` | SKU/gate entitlements |
| `migrations/0010_max_devices.sql` | Max-devices gate |
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
| `sync.push.test.ts` | Batch push |
| `sync_eligibility.test.ts` | Ban/revoke/expiry eligibility |
| `sku_entitlements.test.ts` | SKU gate |
| `sku_max_devices.test.ts` | Max-devices gate |
| `claim.test.ts` | Claim endpoint |
| `control.test.ts` | Control list |
| `handlers.test.ts` | Admin/records handlers |
| `admin.test.ts` + `admin.test.parts/` | Admin session flow |
| `viewer.test.ts` | PWA viewer |
| `update.test.ts` | Update endpoint |
| `purge.test.ts` | Purge endpoint |
| `integration.test.ts` | Full lifecycle (generate→claim→verify chain) |
| `integration_security.test.ts` | Security integration |
| `lifecycle.test.ts` | License lifecycle |
| `web/token.test.ts` | Web-session token |
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
| T009 | Integration generate→claim→verify chain | ✅ Landed |
| T010 | Perf/vitest regression gate | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| `recordsHandler` full table scan of revocations + used_nonces | `routes/records/query.ts` | P1 |
| Configurable `summary_limit` (default 2000, max 5000) for machine summaries | `routes/records/query.ts` | ✅ |
| Dynamic `import()` in hot path | `routes/generate.ts` | P2 |
| D1 query error handling in most routes | `routes/generate.ts` | P2 |
