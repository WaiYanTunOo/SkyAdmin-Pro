#!/usr/bin/env bash
# One-time Ubuntu setup: system packages, venv, deps, desktop shortcut.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== SkyAdmin Pro — Linux setup ==="
echo "Project: $ROOT"
echo ""

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This script is for Linux. On Windows use packaging\\build.ps1"
    exit 1
fi

MISSING_APT=()
for pkg in python3 python3-venv python3-tk python3-pip; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        MISSING_APT+=("$pkg")
    fi
done

if [[ ${#MISSING_APT[@]} -gt 0 ]]; then
    echo "Installing system packages: ${MISSING_APT[*]}"
    sudo apt update
    sudo apt install -y "${MISSING_APT[@]}"
else
    echo "System packages OK."
fi

chmod +x "$ROOT/SkyAdminPro.sh"

echo "Creating virtual environment…"
python3 -m venv "$ROOT/.venv"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
pip install --upgrade pip
pip install -r "$ROOT/requirements.txt"
md5sum "$ROOT/requirements.txt" | awk '{print $1}' > "$ROOT/.venv/.deps_stamp"

echo "Generating application icon…"
python "$ROOT/packaging/make_icon.py"

DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/skyadmin-pro.desktop"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SkyAdmin Pro
GenericName=Accounting Admin
Comment=Accounting and company administration
Exec=${ROOT}/SkyAdminPro.sh
Icon=${ROOT}/icon.png
Path=${ROOT}
Terminal=false
Categories=Office;Finance;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# Optional Desktop shortcut (Ubuntu default)
if [[ -d "$HOME/Desktop" ]]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/SkyAdmin Pro.desktop"
    chmod +x "$HOME/Desktop/SkyAdmin Pro.desktop"
    if command -v gio >/dev/null 2>&1; then
        gio set "$HOME/Desktop/SkyAdmin Pro.desktop" metadata::trusted true 2>/dev/null || true
    fi
    echo "Desktop shortcut: ~/Desktop/SkyAdmin Pro.desktop"
fi

echo ""
echo "Setup complete."
echo ""
echo "Launch options:"
echo "  1. Applications menu → SkyAdmin Pro"
echo "  2. Double-click: SkyAdminPro.sh"
echo "  3. Terminal:       ./SkyAdminPro.sh"
echo ""
