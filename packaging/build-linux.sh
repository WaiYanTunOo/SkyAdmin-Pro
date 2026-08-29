#!/usr/bin/env bash
# Build a single-file Linux executable (similar to SkyAdminPro.exe on Windows).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Run this script on Linux."
    exit 1
fi

VENV_PY="$ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
    echo "Run ./packaging/setup-linux.sh first."
    exit 1
fi

"$VENV_PY" -m pip install "pyinstaller>=6.0.0"
"$VENV_PY" -m pytest tests/ -v --tb=short
"$VENV_PY" "$ROOT/packaging/make_icon.py"
"$VENV_PY" -m PyInstaller "$ROOT/packaging/SkyAdminPro-linux.spec" --noconfirm --log-level WARN

OUT="$ROOT/dist/SkyAdminPro"
if [[ -x "$OUT" ]]; then
    SIZE_MB="$(du -m "$OUT" | awk '{print $1}')"
    echo ""
    echo "Built: $OUT (${SIZE_MB} MB)"
    echo "Run:   $OUT"
    echo "Or copy dist/SkyAdminPro anywhere and double-click (mark executable)."
else
    echo "Build failed — dist/SkyAdminPro not found." >&2
    exit 1
fi
