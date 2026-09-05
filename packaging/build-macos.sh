#!/usr/bin/env bash
# Build SkyAdmin Pro .app bundle on macOS with optional notarization.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Run this script on macOS."
    exit 1
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
if [[ -d "$APP" ]]; then
    echo ""
    echo "Built: $APP"
    echo "Run:   open \"$APP\""
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
