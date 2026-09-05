# Windows code signing

SkyAdmin Pro builds are **unsigned by default**. Windows SmartScreen may warn on first run until you configure Authenticode signing.

## Cost & options (no free public trust for closed-source apps)

There is **no free publicly-trusted code-signing certificate** for proprietary software (Let's Encrypt doesn't issue them; SignPath.io is free for genuine open-source only). Cheapest legitimate routes, roughly cheapest first — recheck pricing before buying:

| Option | Cost (typical, 2026) | SmartScreen | Notes |
|--------|----------------------|-------------|-------|
| Stay unsigned | $0 | Warns forever ("Unknown publisher") | Current default; fine for dev/internal |
| Self-signed cert | $0 | Still warns for customers | Only silences machines where you install the cert |
| Microsoft Store listing | ~$19 one-time (individual) | Trusted (Store-signed) | Requires MSIX repackaging + Store review; not wired up |
| Azure Trusted Signing | Low metered monthly fee (check Azure pricing) | Trusted via Microsoft | No USB token; works with GitHub Actions; see below |
| OV certificate (reseller) | ~$100–250/yr | Trust builds over weeks of downloads | Needs org validation; PFX works in CI today |
| EV certificate | ~$200–500/yr | Instant trust | Key must live on USB token/HSM — painful in CI |

**Recommendation:** Azure Trusted Signing if you want trust without a token ceremony; OV via reseller if you prefer a plain annual cert. This repo supports PFX, store/thumbprint, `/a`, and Azure paths in `sign-windows.ps1` — no code changes needed whichever you pick.

## What is wired up

| Step | Script | Signs |
|------|--------|-------|
| Portable exe | `packaging/build.ps1` | `dist/SkyAdminPro.exe` |
| Installer | `packaging/build-installer.ps1` | portable exe + `dist/SkyAdminPro-Setup-<version>.exe` |
| CI release | `.github/workflows/release.yml` | portable exe when secrets are set |

All paths call `packaging/sign-windows.ps1`, which **skips gracefully** when no certificate is configured (local dev).

## Recommended setup

1. Obtain an **Authenticode** certificate (EV recommended for immediate SmartScreen trust).
2. Install `signtool.exe` (Windows SDK → Signing Tools for Desktop Apps).
3. Export the certificate as `.pfx` or install it in `CurrentUser\My`.

### Local signing (PFX file)

```powershell
$env:SKYADMIN_SIGN_PFX = "C:\certs\skyadmin.pfx"
$env:SKYADMIN_SIGN_PASSWORD = "your-pfx-password"

.\packaging\build-installer.cmd
# Or sign an existing build:
.\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe, dist\SkyAdminPro-Setup-0.3.2.exe
```

### Local signing (certificate store / USB token)

```powershell
# Auto-select a code-signing cert from CurrentUser\My
.\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe

# Or pin a thumbprint
$env:SKYADMIN_SIGN_THUMBPRINT = "ABCDEF1234..."
.\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe
```

### Azure Trusted Signing (no local cert needed)

```powershell
$env:AZURE_TRUSTED_SIGNING_VAULT_URL = "https://<account>.trustedsigning.azure.net/"
$env:AZURE_TRUSTED_SIGNING_CERT = "<certificate-profile-name>"
# Service principal (skip all three on machines with managed identity):
$env:AZURE_TRUSTED_SIGNING_CLIENT_ID = "<app-id>"
$env:AZURE_TRUSTED_SIGNING_SECRET = "<secret>"
$env:AZURE_TRUSTED_SIGNING_TENANT_ID = "<tenant-id>"

.\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe
# Installs AzureSignTool via `dotnet tool` if missing (.NET SDK required).
```

### Force signing (fail if cert missing)

```powershell
.\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe -Required
# Or:
$env:SKYADMIN_SIGN_REQUIRED = "1"
```

## CI secrets (GitHub Actions)

Store in repository secrets:

| Secret | Purpose |
|--------|---------|
| `WINDOWS_CERT_PFX` | Base64-encoded `.pfx` |
| `WINDOWS_CERT_PASSWORD` | PFX password |
| `AZURE_TRUSTED_SIGNING_VAULT_URL` | Trusted Signing account URL (alternative to PFX) |
| `AZURE_TRUSTED_SIGNING_CERT` | Certificate profile name |
| `AZURE_TRUSTED_SIGNING_CLIENT_ID` | Service principal app ID (optional with managed identity) |
| `AZURE_TRUSTED_SIGNING_SECRET` | Service principal secret |
| `AZURE_TRUSTED_SIGNING_TENANT_ID` | Azure tenant ID |

When both are set, the release workflow signs `dist/SkyAdminPro.exe` and runs `release_check.py --require-signature`.

Encode a PFX for GitHub:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\certs\skyadmin.pfx")) | Set-Clipboard
```

## Verify signature

```powershell
Get-AuthenticodeSignature dist\SkyAdminPro.exe
python scripts\release_check.py --skip-pytest --require-signature
```

## macOS notarization

See `packaging/build-macos.sh` — requires Apple Developer ID + `notarytool` + stapler. Documented in `packaging/README.md`.
