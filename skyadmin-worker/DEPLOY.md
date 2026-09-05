# SkyAdmin Worker — production deploy

The Worker issues Ed25519 licenses (`POST /api/generate`), serves the signed
control list (`GET /api/control` → `SKYCTRL2:`), and records global
one-time-use burns (`POST /api/claim`).

## Prerequisites

- Cloudflare account with Workers + D1 enabled
- `npm` and `npx wrangler` (see `package.json`)

## First-time setup

```bash
cd skyadmin-worker
npm ci
cp .dev.vars.example .dev.vars   # edit locally — never commit
```

### 1. Create / bind D1

`wrangler.jsonc` already references database `skyadmin-db`. Apply **versioned migrations** (required):

```bash
npm run db:migrate        # remote D1 — wrangler d1 migrations apply
# npm run db:migrate:local  # local dev only
```

**Deprecated:** `npm run db:init` / applying `schema.sql` directly. That path exits with an error.
`schema.sql` remains an end-state reference only.

### 2. Configure secrets

Set these on the Worker (production uses `wrangler secret put`):

| Secret | Purpose |
|---|---|
| `LICENSE_ED25519_PRIVATE_KEY_B64` | **Required** — PKCS#8 PEM (standard base64) for license/passcode/control signing |
| `API_TOKEN` | Bearer token for owner tools (`LicenseGenerator_iPhone.html`, CLI) |
| `ADMIN_PATH` | Random path segment for hidden admin UI |
| `ADMIN_PASS` | Admin login password |
| `LICENSE_SECRET` | Legacy name — admin session cookie salt (or use `ADMIN_SESSION_SECRET`) |

Generate an Ed25519 keypair (must match `skyadmin_pro/services/license_public.py`):

```bash
python -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64
key = Ed25519PrivateKey.generate()
pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
print('PRIVATE (Worker secret):')
print(base64.b64encode(pem).decode())
print('PUBLIC (embed in license_public.py):')
print(key.public_key().public_bytes_raw().hex())
"
```

### 3. Deploy

```bash
npm run typecheck
npm test
npm run deploy
```

### 4. Smoke test

```bash
curl -s https://YOUR-WORKER.workers.dev/api/ping
curl -s "https://YOUR-WORKER.workers.dev/api/control" | head -c 80
```

Control output must start with `SKYCTRL2:`.

### 5. Apply pending migrations (existing deployments)

If the Worker was deployed before newer migrations, apply pending files:

```bash
npm run db:migrate
```

## Desktop app configuration

Encode your Worker URL in `skyadmin_pro/config.py` as `API_BASE_URL` (byte-array
obfuscation). When set, the desktop app:

1. Pulls revocations/bans from `/api/control` (API-only — no Gist fallback)
2. Requires daily online sync
3. Calls `/api/claim` on activation to burn codes globally

Legacy GitHub Gist (`REVOCATION_URL`) still works only when `API_BASE_URL` is
empty, and must publish `SKYCTRL2:` envelopes (not `SKYCTRL1`).

## Pricing packages (admin)

The hidden admin page can edit package names, days, and Baht prices. Values are
stored in D1 (`control_meta.pricing_packages`) and served publicly at
`GET /api/pricing` (desktop activation dialog + iPhone generator).

Check signing-key alignment after deploy:

```bash
curl -s https://YOUR-WORKER.workers.dev/api/signing/public-key
```

`matches_desktop` must be `true` or activation codes from the admin site will
fail in the desktop app.

Rotate Ed25519 keys together:

1. Generate new keypair (see above)
2. Update Worker secret `LICENSE_ED25519_PRIVATE_KEY_B64`
3. Update `ED25519_PUBLIC_KEY_HEX` in `license_public.py` + `verification.ts`
4. Ship a new desktop build
5. Re-issue outstanding licenses (old signatures will fail verification)
