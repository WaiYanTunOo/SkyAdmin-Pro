#!/usr/bin/env bash
# SkyAdmin Pro — Ubuntu / Linux launcher (double-click or run from terminal).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

die() {
    if command -v zenity >/dev/null 2>&1 && [[ -n "${DISPLAY:-}" ]]; then
        zenity --error --width=420 --text="$1" 2>/dev/null || echo "ERROR: $1" >&2
    else
        echo "ERROR: $1" >&2
    fi
    exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
    die "Python 3 is not installed.\n\nRun once:\n  ./packaging/setup-linux.sh"
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    die "Tkinter is missing (required for the GUI).\n\nRun once:\n  ./packaging/setup-linux.sh"
fi

VENV="$ROOT/.venv"
if [[ ! -d "$VENV" ]]; then
    echo "First launch — creating virtual environment…"
    python3 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

STAMP="$VENV/.deps_stamp"
REQ_HASH="$(md5sum "$ROOT/requirements.txt" | awk '{print $1}')"
if [[ ! -f "$STAMP" ]] || [[ "$(cat "$STAMP")" != "$REQ_HASH" ]]; then
    echo "Installing / updating Python dependencies…"
    pip install --upgrade pip >/dev/null
    pip install -r "$ROOT/requirements.txt"
    echo "$REQ_HASH" > "$STAMP"
fi

if [[ ! -f "$ROOT/icon.png" ]]; then
    python "$ROOT/packaging/make_icon.py" 2>/dev/null || true
fi

exec python "$ROOT/main.py" "$@"
