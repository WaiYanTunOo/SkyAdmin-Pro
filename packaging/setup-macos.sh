#!/usr/bin/env bash
# One-time macOS setup: venv + dependencies.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This script is for macOS."
    exit 1
fi

if ! xcode-select -p >/dev/null 2>&1; then
    echo "Install Xcode Command Line Tools first:"
    echo "  xcode-select --install"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Install Python 3.11+ (python.org or Homebrew)."
    exit 1
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Tkinter is missing. On Homebrew: brew install python-tk@3.12"
    exit 1
fi

echo "Creating virtual environment…"
python3 -m venv "$ROOT/.venv"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
pip install --upgrade pip
pip install -r "$ROOT/requirements.txt" -r "$ROOT/requirements-dev.txt"
shasum -a 256 "$ROOT/requirements.txt" | awk '{print $1}' > "$ROOT/.venv/.deps_stamp"

python "$ROOT/packaging/make_icon.py"
echo ""
echo "Setup complete. Run: python main.py"
echo "Build app: ./packaging/build-macos.sh"
