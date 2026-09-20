"""Application identity, version resolution, and default appearance constants."""

from __future__ import annotations

import sys
from pathlib import Path


def _resolve_app_version() -> str:
    """Read version from pyproject.toml (dev + frozen bundle) with safe fallback."""
    try:
        import tomllib

        candidates: list[Path] = []
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / "pyproject.toml")
        root = Path(__file__).resolve().parents[1]
        candidates.extend([root / "pyproject.toml", Path.cwd() / "pyproject.toml"])
        for path in candidates:
            if not path.is_file():
                continue
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            version = data.get("project", {}).get("version")
            if version:
                return str(version)
    except (OSError, ValueError):
        pass
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("skyadmin-pro")
    except ImportError:
        pass
    return "0.3.6"


APP_NAME = "SkyAdmin Pro"
APP_TAGLINE = "Wai Yan Tun Oo (SKY)"
APP_VERSION = _resolve_app_version()

# Default appearance — Settings will override from SQLite.
DEFAULT_APPEARANCE_MODE = "light"  # "dark" | "light" | "system"
DEFAULT_COLOR_THEME = "blue"
