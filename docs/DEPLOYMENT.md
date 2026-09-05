# Deployment Runbook

## 1. Desktop App — Windows Build

### Portable EXE

```powershell
.\packaging\build.ps1
# Output: dist/SkyAdminPro.exe
```

Steps: pytest → generate icon → PyInstaller build → optional code signing → release_check.

### Installer (Inno Setup 6)

```powershell
.\packaging\build-installer.ps1
# Output: dist/SkyAdminPro-Setup-{version}.exe
```

Requires Inno Setup 6 (`winget install JRSoftware.InnoSetup`). Builds portable exe first, then compiles installer.

### Code Signing

Signing is optional and handled by `packaging/sign-windows.ps1`. Set `SKYADMIN_SIGN_REQUIRED=1` to enforce signing during build.

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

### D1 Database Setup

```bash
# Create database (first time only)
npx wrangler d1 create skyadmin-db

# Option A: Apply all migrations (recommended for new databases)
npx wrangler d1 migrations apply skyadmin-db --remote

# Option B: Apply monolithic schema (legacy, still works)
npx wrangler d1 execute skyadmin-db --remote --file=schema.sql
```

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

1. **D1 migration**: Run `npx wrangler d1 execute skyadmin-db --remote --file=schema.sql` from `skyadmin-worker/`.
2. **Admin account**: Set `ADMIN_PASS` in environment variables. Access admin panel at `/{ADMIN_PATH}`.
3. **Desktop DB**: SQLite schema auto-applies on first app launch via `skyadmin_pro/db/schema.py`.

## 5. Updates

### Version Bump

Update version in `skyadmin_pro/config.py` (`APP_VERSION`).

### Pre-ship Gate

```bash
python scripts/release_check.py
# Checks: pytest, exe size, forbidden strings, version consistency, Worker endpoint
# Options: --skip-pytest, --exe path/to/SkyAdminPro.exe
```

### Publish Release

```bash
# Local publish (release_check + release notes)
python scripts/publish_release.py --version 0.3.1 --exe dist/SkyAdminPro.exe

# With GitHub release
python scripts/publish_release.py --version 0.3.1 --exe dist/SkyAdminPro.exe --github

# Worker-only update line (no GitHub release)
python scripts/publish_release.py --version 0.3.1 --url https://github.com/.../releases/...
```
