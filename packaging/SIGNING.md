# Windows code signing

SkyAdmin Pro builds are **unsigned by default**. Windows SmartScreen may warn on first run until you configure Authenticode signing.

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
.\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe, dist\SkyAdminPro-Setup-0.3.1.exe
```

### Local signing (certificate store / USB token)

```powershell
# Auto-select a code-signing cert from CurrentUser\My
.\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe

# Or pin a thumbprint
$env:SKYADMIN_SIGN_THUMBPRINT = "ABCDEF1234..."
.\packaging\sign-windows.ps1 -Paths dist\SkyAdminPro.exe
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
