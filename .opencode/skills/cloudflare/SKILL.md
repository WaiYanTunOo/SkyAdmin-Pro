---
name: cloudflare
description: Use when operating the Cloudflare platform for SkyAdmin Pro — Workers deploys, D1 database ops, Queues, secrets, bindings, tail/logs, and edge limits. Complements skyadmin-worker (code) with platform operations.
---

# Cloudflare Platform Skill (SkyAdmin Pro)

## Where things live

- Worker: `skyadmin-worker/` (`wrangler.jsonc` → `skyadmin-worker`, D1 binding `DB` → `skyadmin-db`)
- Prod URL: `https://skyadmin-worker.skyadmin-pro.workers.dev`
- Admin dashboard: `https://skyadmin-worker.skyadmin-pro.workers.dev/<ADMIN_PATH>`
- D1: `skyadmin-db` (prod) + `skyadmin-db-staging` (blocked on real DB id — see `DEPLOY.md`)
- CI deploy: `.github/workflows/deploy.yml` (`environment: production`)

## What data Cloudflare holds (and does NOT hold)

D1 is the **licensing + control plane**, not a full data mirror:

| Table | Content |
|---|---|
| `issued_licenses` | Minted keys/passcodes, machine binding, expiry |
| `used_nonces` | Burned one-time codes (pruned for expired/revoked) |
| `revocations`, `revoked_passcodes`, `bans` | Control list (capped at 5000 newest in envelope) |
| `sync_devices` | `token_hash` + 30-day TTL per machine (no plaintext tokens) |
| `sync_rows` | **Per-device namespaces** `(machine_id, table, global_id)` — echo/backup + viewer, no cross-device fan-out |
| `sync_conflicts` | Merge log (90-day retention) |
| `control_meta` | Pricing packages, `latest_version`/`latest_url` (update channel) |
| `admin_audit_log`, `login_attempts`, `rate_limits` | Ops/security (purged periodically) |

Desktop source of truth stays local: `%USERPROFILE%\.skyadmin_pro\skyadmin_pro.db`
(SQLCipher), workspace folders, `.skybackup` archives. Cloudflare never sees
IRD/vault passwords (never synced — `SYNC_EXCLUDED_COLUMNS`) or full documents.

## Wrangler operations

```bash
cd skyadmin-worker
npx wrangler dev                    # local dev (needs .dev.vars, never commit)
npx wrangler d1 migrations apply skyadmin-db --remote   # versioned migrations only
npx wrangler secret put API_TOKEN   # secrets: API_TOKEN, ADMIN_PATH, ADMIN_PASS,
                                    # ADMIN_SESSION_SECRET (preferred), LICENSE_ED25519_PRIVATE_KEY_B64
npx wrangler deploy                 # prod (CI gates environment: production)
npx wrangler tail                   # live logs
npx wrangler d1 execute skyadmin-db --remote --command "SELECT count(*) FROM sync_rows"
```

Rules: migrations dir only (`migrations/NNNN_*.sql`, never replay `schema.sql`
— `db:init` exits with error); `npm run typecheck && npm test` before every
deploy; staging env needs a real `database_id` first.

## Secrets reference

| Secret | Purpose |
|---|---|
| `LICENSE_ED25519_PRIVATE_KEY_B64` | PKCS#8 base64 — all signing (must match desktop `license_public.py`) |
| `API_TOKEN` | Bearer for owner tools/CLI (never in DOM — S5) |
| `ADMIN_PATH` | Random segment for hidden admin UI |
| `ADMIN_PASS` | Admin login password (constant-time compare, rate-limited) |
| `ADMIN_SESSION_SECRET` | Session cookie salt (preferred; `LICENSE_SECRET` is legacy alias) |

## Edge limits that shape the protocol

- CPU time 10–50ms per request → push capped at 500 changes, 64KB/row,
  D1 batches of 100, per-endpoint rate limits (30–60/min).
- No Cloudflare Queues yet — revisit only on measured CPU pressure
  (see `docs/CRDT_DESIGN.md` §7).
- D1 batch-statement + SQLite 999-variable ceilings → chunked deletes
  (≤400 ids), chunked lookups (400 rows).

## Deploy checklist

1. `npm run typecheck && npm test` green
2. `npx wrangler d1 migrations apply skyadmin-db --remote`
3. `npx wrangler deploy`
4. Smoke: `/api/ping` ok, `/api/signing/public-key` `matches_desktop: true`,
   `/api/pricing` packages present, admin login + CSRF works
5. Never publish a test version to `/api/update` on prod (banners all desktops);
   never mint test passcodes on prod (pollutes Records)
