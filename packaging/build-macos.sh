#!/usr/bin/env bash
# Build SkyAdmin Pro .app bundle on macOS with optional notarization.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Run this script on macOS."
    exit 1
fi

# ── Docker-based testing option (CI-03) ──────────────────────────
# To run tests in a reproducible Docker environment instead of the
# host system, set USE_DOCKER=1 before invoking this script:
#
#   USE_DOCKER=1 ./packaging/build-macos.sh
#
# This spins up a python:3.12-slim container, installs dependencies,
# runs the test suite inside it, then proceeds with the build.
# Useful for CI parity checks and verifying that the build works
# from a clean environment.
# ──────────────────────────────────────────────────────────────────

if [[ "${USE_DOCKER:-0}" == "1" ]]; then
    if ! command -v docker &>/dev/null; then
        echo "USE_DOCKER=1 requires Docker but it is not installed." >&2
        exit 1
    fi
    echo "Running tests in Docker container..."
    docker run --rm -v "$ROOT:$ROOT" -w "$ROOT" python:3.12-slim bash -c '
        python -m pip install --upgrade pip
        pip install -r requirements.txt -r requirements-dev.txt
        xvfb-run pytest tests/ -q --tb=short --ignore=tests/test_performance_clients.py --ignore=tests/test_performance_stress.py
    '
    echo "Docker test pass."
fi

VENV_PY="$ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "Run ./packaging/setup-macos.sh first."
    exit 1
fi

"$VENV_PY" -m pip install "pyinstaller>=6.0.0"
"$VENV_PY" -m pytest tests/ -q --tb=short
"$VENV_PY" "$ROOT/packaging/make_icon.py"
"$VENV_PY" -m PyInstaller "$ROOT/packaging/SkyAdminPro-macos.spec" --noconfirm --log-level WARN

APP="$ROOT/dist/SkyAdminPro.app"
MACOS_BIN="$APP/Contents/MacOS/SkyAdminPro"
if [[ -d "$APP" ]]; then
    echo ""
    echo "Built: $APP"
    echo "Run:   open \"$APP\""
    echo ""
    echo "Running release checks..."
    "$VENV_PY" "$ROOT/scripts/release_check.py" --skip-pytest --exe "$MACOS_BIN" --skip-installer
else
    echo "Build failed — dist/SkyAdminPro.app not found." >&2
    exit 1
fi

# ── Notarization (optional) ──────────────────────────────────────────────
# Requires: APPLE_ID, APPLE_TEAM_ID, APPLE_APP_PASSWORD in environment
# Sign first: codesign --force --deep --sign "Developer ID Application: ..." "$APP"
# Then notarize:
if [[ "${NOTARIZE:-0}" == "1" ]]; then
    if [[ -z "${APPLE_ID:-}" || -z "${APPLE_TEAM_ID:-}" || -z "${APPLE_APP_PASSWORD:-}" ]]; then
        echo "Set APPLE_ID, APPLE_TEAM_ID, APPLE_APP_PASSWORD to notarize." >&2
        exit 1
    fi
    ZIP="$ROOT/dist/SkyAdminPro.zip"
    ditto -c -k --keepParent "$APP" "$ZIP"
    echo "Submitting for notarization..."
    xcrun notarytool submit "$ZIP" \
        --apple-id "$APPLE_ID" \
        --team-id "$APPLE_TEAM_ID" \
        --password "$APPLE_APP_PASSWORD" \
        --wait
    echo "Stapling notarization ticket..."
    xcrun stapler staple "$APP"
    rm -f "$ZIP"
    echo "Notarized: $APP"
fi
