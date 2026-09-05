---
name: skyadmin-worker
description: Use when working on skyadmin-worker/ routes, sync, license, D1 database, or Cloudflare Worker configuration. Handles Hono routes, Vitest, wrangler deploy patterns.
---

# SkyAdmin Pro — Worker API Skill

## Key Files

- `skyadmin-worker/src/index.ts` — Hono app entry, all route wiring
- `skyadmin-worker/src/db.ts` — D1 database helper queries + Env binding types
- `skyadmin-worker/src/auth.ts` — Bearer-token / admin session cookie middleware
- `skyadmin-worker/src/signing.ts` — Ed25519 signing, license keys, passcodes, control envelope
- `skyadmin-worker/src/verification.ts` — Ed25519 verification / activation-code claim parsing
- `skyadmin-worker/src/license_policy.ts` — Activation window + package-duration rules
- `skyadmin-worker/src/sync_*.ts` — Sync schema, auth, eligibility, push logic
- `skyadmin-worker/src/routes/` — All route handlers
- `skyadmin-worker/schema.sql` — D1 schema (12+ tables + indexes)
- `skyadmin-worker/wrangler.jsonc` — Worker config + D1 binding
- `skyadmin-worker/vitest.config.ts` — Vitest config

## API Endpoints

### Public
- `GET /api/ping` — Health check
- `GET /api/control` — SKYCTRL2-signed control list (REVOKE, BAN, USED, LATEST)
- `POST /api/claim` — Global one-time-use activation claim
- `POST /api/sync/register` — Exchange claim for 30-day sync token
- `GET /api/sync/schema` — Get synced table manifest
- `GET /api/sync/pull` — Pull synced data
- `POST /api/sync/push` — Push synced data (last-write-wins)
- `GET /api/signing/public-key` — Ed25519 public key
- `GET /api/pricing` — Pricing packages (public read)
- `GET /api/update` — Desktop version/URL
- `GET /viewer` — Read-only mobile PWA viewer

### Authenticated (Bearer/Owner)
- `POST /api/generate` — Mint license keys
- `POST /api/revoke` / `POST /api/unrevoke` — Revoke/unrevoke licenses
- `POST /api/ban` / `POST /api/unban` / `GET /api/bans` — Machine bans
- `POST /api/used` / `POST /api/revoke-pc` — Mark nonce used / revoke passcodes
- `GET /api/records` — Paginated license records
- `POST /api/purge-licenses` — Archive+delete stale licenses
- `POST /api/pricing` — Update pricing (admin)
- `POST /api/update` — Publish desktop version (admin)

## Architecture

### Hono Framework
- Lightweight TypeScript web framework
- Middleware chain: CORS → CSP → Auth → Rate Limit → Route Handler
- Route grouping via `app.route()`

### D1 Database
- SQLite at the edge via Cloudflare D1
- Schema in `schema.sql` with migrations in `migrations/`
- Batch operations for atomic multi-statement transactions

### Security
- Ed25519 digital signatures for all license operations
- HMAC session tokens for admin dashboard
- Timing-safe comparisons (`timing_safe.ts`)
- Per-IP/per-key rate limiting (`rate_limit.ts`)
- Strict CORS fail-closed for cross-origin callers
- CSP headers with per-response script nonces
- Admin login lockout with per-IP blocking

### Sync Protocol
- Tables: `clients`, `tasks`, `office_contacts`, `notebook_entries`
- Last-write-wins conflict resolution
- Sensitive columns stripped before upload (e.g. `clients.ird_password`)
- 30-day sliding device sync tokens

## Conventions

- TypeScript strict mode
- Vitest for all tests (`src/**/*.test.ts`)
- `wrangler dev` for local development
- `wrangler deploy` for production
- D1 migrations in `migrations/` directory
- All routes in `src/routes/` directory
- Middleware in `src/` root
