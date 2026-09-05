# SkyAdmin Pro — cross-platform packaging

## Windows (primary)

```powershell
# One-time
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt

# Build portable exe
.\packaging\build.cmd
# Or if scripts are allowed: .\packaging\build.ps1
# Output: dist\SkyAdminPro.exe
```

If PowerShell reports *running scripts is disabled*, use `build.cmd` (recommended) or:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1
```

### Windows installer (Inno Setup)

Requires [Inno Setup 6](https://jrsoftware.org/isdl.php) (or `winget install JRSoftware.InnoSetup`):

```powershell
.\packaging\build-installer.cmd
# Or: .\packaging\build-installer.ps1
# Output: dist\SkyAdminPro-Setup-<version>.exe
```

ISCC is searched in `Program Files`, `Program Files (x86)`, and `%LOCALAPPDATA%\Programs\Inno Setup 6\`.

The installer places the app under `Program Files`, adds Start Menu shortcut, optional desktop icon. User data (`%USERPROFILE%\.skyadmin_pro`) is **not** removed on uninstall.

Pre-ship gate:

```powershell
python scripts\release_check.py
# When signing is configured:
python scripts\release_check.py --require-signature
```

See `packaging/SIGNING.md` for Authenticode certificate setup.

## Linux (Ubuntu / Debian)

```bash
# One-time setup (apt packages, venv, desktop shortcut)
chmod +x packaging/setup-linux.sh SkyAdminPro.sh
./packaging/setup-linux.sh

# Dev run (no build)
./SkyAdminPro.sh

# Single-file binary (on Linux only)
./packaging/build-linux.sh
# Output: dist/SkyAdminPro
```

Requirements: `python3`, `python3-tk`, `python3-venv`, X11 or Wayland display for GUI.

## macOS (developer builds — not notarized)

```bash
chmod +x packaging/setup-macos.sh packaging/build-macos.sh
./packaging/setup-macos.sh
./packaging/build-macos.sh
# Output: dist/SkyAdminPro.app
```

Notes:

- Install **Xcode Command Line Tools**: `xcode-select --install`
- Tkinter ships with python.org installer or Homebrew `python-tk@3.12`
- **Notarization** is required for distribution outside your Mac — see Apple Developer docs
- Gatekeeper may block unsigned builds: right-click → Open the first time

## Publish an app update (all platforms)

After a tagged release (recommended):

```bash
# CI does this automatically on git tag v* when SKYADMIN_API_TOKEN is set.
# Manual one-shot after a local build:
python scripts/publish_release.py --version 0.3.2 --exe dist/SkyAdminPro.exe --github
```

Or publish only the Worker LATEST line (URL must already be public):

```bash
# Bearer token = Worker API_TOKEN
python scripts/publish_update.py --version 0.3.2 --url https://github.com/WaiYanTunOo/SkyAdmin-Pro/releases/download/v0.3.2/SkyAdminPro.exe
```

Update `CHANGELOG.md` before tagging:

```bash
python scripts/generate_changelog.py --version 0.3.2 --write
git add CHANGELOG.md && git commit -m "Changelog for 0.3.2"
git tag v0.3.2 && git push origin v0.3.2
```

Or use **Admin → App update** on the Worker admin page.

Desktop apps pick up `LATEST version url` on the next **Sync Now** or daily control-list fetch and show **Settings → Download**.

## Files

| File | Purpose |
|------|---------|
| `SkyAdminPro.spec` | Windows PyInstaller spec |
| `packaging/SkyAdminPro-linux.spec` | Linux single-file spec |
| `packaging/SkyAdminPro-macos.spec` | macOS `.app` bundle spec |
| `packaging/build.ps1` | Windows build + tests |
| `packaging/build-installer.ps1` | Windows Inno Setup installer |
| `packaging/sign-windows.ps1` | Authenticode signing (optional) |
| `packaging/SkyAdminPro.iss` | Inno Setup script |
| `packaging/build-linux.sh` | Linux build + tests |
| `packaging/build-macos.sh` | macOS build + tests |
| `scripts/release_check.py` | Automated pre-release gate |
| `scripts/generate_changelog.py` | Release notes from git history |
| `scripts/publish_release.py` | Local publish orchestrator |
| `scripts/publish_update.py` | Worker LATEST update line |
