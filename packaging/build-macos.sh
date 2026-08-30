#!/usr/bin/env bash
# Build SkyAdmin Pro .app bundle on macOS (unsigned — dev use).
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
    echo "Note: unsigned — right-click → Open on first launch."
else
    echo "Build failed — dist/SkyAdminPro.app not found." >&2
    exit 1
fi
