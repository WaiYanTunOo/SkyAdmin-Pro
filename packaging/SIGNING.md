# Windows code signing (optional)

SkyAdmin Pro builds are **unsigned** by default. Windows SmartScreen may warn on first run.

## Recommended setup

1. Obtain an **Authenticode** certificate (EV recommended for immediate SmartScreen trust).
2. Install `signtool.exe` (Windows SDK).
3. Sign after PyInstaller / Inno Setup:

```powershell
$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
$ts = "http://timestamp.digicert.com"

# Portable exe
& $signtool sign /fd SHA256 /tr $ts /td SHA256 /a dist\SkyAdminPro.exe

# Installer
& $signtool sign /fd SHA256 /tr $ts /td SHA256 /a dist\SkyAdminPro-Setup-*.exe
```

## CI secrets (GitHub Actions)

Store in repository secrets:

| Secret | Purpose |
|--------|---------|
| `WINDOWS_CERT_PFX` | Base64-encoded `.pfx` |
| `WINDOWS_CERT_PASSWORD` | PFX password |

Add a signing step to `.github/workflows/release.yml` after the build (requires `windows-latest` runner with certificate imported).

## macOS notarization

See `packaging/build-macos.sh` — requires Apple Developer ID + `notarytool` + stapler. Documented in `packaging/README.md`.

## Verify signature

```powershell
Get-AuthenticodeSignature dist\SkyAdminPro.exe
```
