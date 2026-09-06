# Deployment Runbook

## 1. Desktop App — Windows Build

### Portable EXE (dev only — not the ship path)

```powershell
.\packaging\build.ps1
# Output: dist/SkyAdminPro.exe
```

Steps: pytest → generate icon → PyInstaller build → optional code signing →
`release_check --skip-installer` (portable path does not require the installer).

### Installer (Inno Setup 6) — ship path

```powershell
.\packaging\build-installer.ps1
# Output: dist/SkyAdminPro-Setup-{version}.exe
```

Requires Inno Setup 6 (`winget install JRSoftware.InnoSetup`). Builds portable exe first, then compiles installer, then runs full `release_check` (installer required).

### Code Signing

Local builds skip signing gracefully via `packaging/sign-windows.ps1`. Set `SKYADMIN_SIGN_REQUIRED=1`
(or pass `-Required`) to enforce it. **`v*` releases always require a signature**: CI fails the
tag pipeline when no certificate is configured — see `packaging/SIGNING.md` for cert options
(PFX, store, Azure Trusted Signing).

## 2. Worker API — Cloudflare Worker

### Configuration

`skyadmin-worker/wrangler.jsonc`:
```jsonc
{
  "name": "skyadmin-worker",
  "main": "src/index.ts",
  "compatibility_date": "2025-09-01",
  "d1_databases": [{ "binding": "DB", "database_name": "skyadmin-db", "database_id": "..." }]
}
```

### Deploy

```bash
cd skyadmin-worker
npx wrangler deploy          # deploy to production
npx wrangler dev             # local dev server
```

CI (`.github/workflows/deploy.yml`) runs typecheck + Vitest, applies D1 migrations, then deploys.
A **concurrency group** (`skyadmin-worker-deploy`, `cancel-in-progress: false`) prevents overlapping migrate+deploy races on `main`.
Optionally add `environment: production` in that workflow after creating a protected GitHub Environment.
*(Note: Staging Worker+D1 and GitHub Environment protection are owner-only steps, not executed by automated agents.)*

### D1 Database Setup

```bash
# Create database (first time only)
npx wrangler d1 create skyadmin-db

# Apply all versioned migrations (required — only supported setup path)
npx wrangler d1 migrations apply skyadmin-db --remote
# Or: npm run db:migrate
```

Do **not** apply `schema.sql` via `wrangler d1 execute` / legacy `npm run db:init`.
That path is **deprecated** and can leave D1 without a migration history.
`schema.sql` is kept as an end-state reference only.

Update `database_id` in `wrangler.jsonc` after creation.

### Creating New Migrations

```bash
# 1. Create a numbered SQL file in migrations/
#    Format: NNNN_description.sql (e.g., 0002_add_column.sql)
# 2. Write DDL statements in the file
# 3. Apply:
npx wrangler d1 migrations apply skyadmin-db --remote
```

Migrations are tracked in D1's internal `_cf_KV` table and only applied once.

## 3. Environment Variables

Set in `skyadmin-worker/.dev.vars` (local) or Cloudflare dashboard (production).

| Variable | Description |
|----------|-------------|
| `LICENSE_SECRET` | Admin session cookie salt (legacy name; prefer `ADMIN_SESSION_SECRET`). |
| `ADMIN_SESSION_SECRET` | Preferred name for admin session cookie salt. |
| `API_TOKEN` | Owner bearer token for protected API endpoints. |
| `ADMIN_PATH` | Random path for admin panel URL. |
| `ADMIN_PASS` | Strong admin password. |
| `LICENSE_ED25519_PRIVATE_KEY_B64` | Ed25519 PKCS#8 PEM key (base64), must match `skyadmin_pro/services/license_public.py`. |

Generate Ed25519 key:
```bash
python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; k=Ed25519PrivateKey.generate(); print(k.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode())" | base64 -w0
```

## 4. First-time Setup

1. **D1 migration**: Run `npx wrangler d1 migrations apply skyadmin-db --remote` from `skyadmin-worker/` (versioned `migrations/` only). Do not replay `schema.sql` — it is reference-only. Apply `0002_sync_devices_expires_at` on any D1 created before sync-token TTL so `POST /api/sync/register` does not 500 on missing `expires_at`. After `0003_sync_tokens_hash`, existing sync devices must **re-register** (plaintext tokens are not copied — D1 SQL cannot hash them). Issue a fresh activation code if the old code was already burned.
2. **Admin account**: Set `ADMIN_PASS` in environment variables. Access admin panel at `/{ADMIN_PATH}`.
3. **Desktop DB**: SQLite schema auto-applies on first app launch via `skyadmin_pro/db/schema.py` + versioned `skyadmin_pro/db/migrations/`.
4. **Support note — reinstalls**: activation codes burn strictly one-time (`used_nonces`). A wiped/reinstalled PC cannot re-register with its old code — issue a fresh code from the admin panel (Generate). Sync tokens additionally expire after 30 days idle and rotate on re-register.
5. **Sync scope — client groups**: `client_groups` syncs by `global_id` (schema v2). Numeric `clients.group_id` is never sent; membership uses `group_global_id`. See `skyadmin_pro/services/data_sync.py`.

## 5. Updates

### Version Bump

Single source of truth: `pyproject.toml` (`project.version`). `APP_VERSION` in `skyadmin_pro/config/` reads it at runtime — do not hardcode versions elsewhere. CI fails the release when a `v*` tag disagrees (`release.yml` tag gate).

### Pre-ship Gate

```bash
python scripts/release_check.py
# Checks: full pytest, signed exe + installer (installer-first ship path),
# forbidden strings, version consistency, Worker endpoints, SHA256SUMS
# Options: --skip-pytest, --skip-worker, --skip-installer, --exe PATH, --require-signature
```

### Publish Release

Auto-update URL must point at the **installer** (`SkyAdminPro-Setup-{version}.exe`), not the portable exe.

```bash
# Local publish (release_check + release notes)
python scripts/publish_release.py --version 0.3.2 --exe dist/SkyAdminPro-Setup-0.3.2.exe

# With GitHub release
python scripts/publish_release.py --version 0.3.2 --exe dist/SkyAdminPro-Setup-0.3.2.exe --github

# Worker-only update line (no GitHub release)
python scripts/publish_release.py --version 0.3.2 --url https://github.com/.../releases/download/v0.3.2/SkyAdminPro-Setup-0.3.2.exe
```

Tag CI (`release.yml`) fail-closes if `SKYADMIN_API_TOKEN` is missing — GitHub Release publish requires the Worker auto-update channel to be updated.
