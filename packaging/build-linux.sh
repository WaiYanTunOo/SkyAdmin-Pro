#!/usr/bin/env bash
# Build a single-file Linux executable + optional AppImage.
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
    echo ""
    echo "Running release checks..."
    "$VENV_PY" "$ROOT/scripts/release_check.py" --skip-pytest --exe "$OUT" --skip-installer --linux-binary "$OUT"
else
    echo "Build failed — dist/SkyAdminPro not found." >&2
    exit 1
fi

# ── AppImage (optional) ──────────────────────────────────────────────────
# Requires: appimagetool on PATH (https://github.com/AppImage/AppImageKit)
if [[ "${BUILD_APPIMAGE:-0}" == "1" ]]; then
    if ! command -v appimagetool &>/dev/null; then
        echo "appimagetool not found — skipping AppImage." >&2
    else
        APPDIR="$ROOT/dist/SkyAdminPro.AppDir"
        mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
        cp "$OUT" "$APPDIR/usr/bin/SkyAdminPro"
        cat > "$APPDIR/SkyAdminPro.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=SkyAdmin Pro
Exec=SkyAdminPro
Icon=SkyAdminPro
Categories=Office;
EOF
        # Copy icon if available
        ICON="$ROOT/dist/SkyAdminPro.png"
        if [[ -f "$ICON" ]]; then
            cp "$ICON" "$APPDIR/usr/share/icons/hicolor/256x256/apps/SkyAdminPro.png"
            cp "$ICON" "$APPDIR/SkyAdminPro.png"
        fi
        chmod +x "$APPDIR/usr/bin/SkyAdminPro"
        appimagetool "$APPDIR" "$ROOT/dist/SkyAdminPro.AppImage" 2>/dev/null
        rm -rf "$APPDIR"
        echo "AppImage: $ROOT/dist/SkyAdminPro.AppImage"
    fi
fi
