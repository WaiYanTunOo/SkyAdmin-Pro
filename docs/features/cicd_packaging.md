# CI/CD & Packaging — Feature Detail

## Purpose
GitHub Actions CI/release/deploy, PyInstaller builds, Inno Setup installer, code signing, release checks.

## Code Files

### Workflows

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Lint (ruff) + pytest + Worker typecheck + Vitest on push |
| `.github/workflows/release.yml` | Tag → build exe + installer → release_check → GitHub Release → Worker publish (gated on `needs: worker`) |
| `.github/workflows/deploy.yml` | Worker test → migrate → deploy; concurrency group `skyadmin-worker-deploy` |

### Scripts

| File | Purpose |
|------|---------|
| `scripts/release_check.py` | Version, exe, installer (skippable), Worker HTTP smoke, pytest |
| `scripts/publish_release.py` | GitHub Release + Worker update on tag |
| `scripts/publish_update.py` | Publish update to `control_meta` |
| `scripts/generate_changelog.py` | Changelog/release notes generator |

### Packaging

| File | Purpose |
|------|---------|
| `packaging/build.ps1` | PyInstaller build (Windows) |
| `packaging/build.cmd` | Batch wrapper |
| `packaging/build_native.ps1` | Native build |
| `packaging/build-installer.ps1` | Inno Setup installer |
| `packaging/build-installer.cmd` | Batch wrapper |
| `packaging/SkyAdminPro.iss` | Inno Setup script |
| `packaging/sign-windows.ps1` | Windows code signing |
| `packaging/build-macos.sh` | macOS build |
| `packaging/setup-macos.sh` | macOS dependencies |
| `packaging/SkyAdminPro-macos.spec` | macOS PyInstaller spec |
| `packaging/build-linux.sh` | Linux build |
| `packaging/setup-linux.sh` | Linux dependencies |
| `packaging/SkyAdminPro-linux.spec` | Linux PyInstaller spec |
| `packaging/README.md` | Build docs |
| `packaging/SIGNING.md` | Signing docs |

## Architecture Decisions
- **Release gate**: `release.yml` publish job `needs: [windows-release, worker]` — Worker Vitest must pass before publish.
- **Fail-closed**: tag release fails if `SKYADMIN_API_TOKEN` GitHub secret missing.
- **Installer update URL**: `SkyAdminPro-Setup-{ver}.exe` published to Worker update channel.
- **Changelog**: `CHANGELOG.md` + `scripts/generate_changelog.py`(Phase 11.5 landed).

## Tests

| File | Covers |
|------|--------|
| `tests/test_release_build.py` | Release check pipeline |
| `tests/test_generate_changelog.py` | Changelog generator |
| `scripts/release_check.py` | Manual pre-ship gate |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 11.1 | CI release job | ✅ Landed |
| Phase 11.2 | Windows code signing | ✅ Landed |
| Phase 11.5 | Changelog generator | ✅ Landed |
| Phase 11.6 | Publish pipeline | ✅ Landed |
| R1.0 | Release gated on Worker Vitest | ✅ Landed |
| Wave D D1 | macOS notarization / Linux polish | Later |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| No dependency vulnerability scanning | `.github/workflows/ci.yml` | P1 |
| No SAST scanning (bandit/semgrep) | `.github/workflows/ci.yml` | P2 |
| No integration tests in CI | `.github/workflows/ci.yml` | P2 |
| No performance regression gate | `.github/workflows/ci.yml` | P2 |
