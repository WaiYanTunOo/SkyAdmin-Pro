from __future__ import annotations

import logging
import sys
from pathlib import Path

from skyadmin_pro.services.license._constants import LICENSE_FILENAME


def _saved_license_text() -> str | None:
    try:
        from skyadmin_pro.paths import app_data_dir

        path = app_data_dir() / LICENSE_FILENAME
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            return text or None
    except (OSError, ValueError):
        pass
    return None


def _is_repair_activation(code: str) -> bool:
    """True when re-pasting the exact code already stored on this machine."""
    saved = _saved_license_text()
    if not saved:
        return False
    return "".join((code or "").split()) == "".join(saved.split())


def _shadow_path() -> Path | None:
    """Shadow copy lives beside the database backups (same machine only)."""
    try:
        from skyadmin_pro.paths import app_data_dir

        return app_data_dir() / "backups" / "license.key.shadow"
    except (ImportError, OSError):
        return None


def _self_heal_license() -> Path | None:
    """If the license file was deleted (cleaner tools/AV), restore it from
    the shadow copy — same machine, same hardware binding."""
    shadow = _shadow_path()
    if shadow is None or not shadow.exists():
        return None
    try:
        from skyadmin_pro.paths import app_data_dir

        primary = app_data_dir() / LICENSE_FILENAME
        if not primary.exists():
            primary.write_text(shadow.read_text(encoding="utf-8"), encoding="utf-8")
            logging.getLogger(__name__).info("License file was missing — restored from shadow copy.")
            return primary
    except (OSError, ValueError):
        return None
    return None


def _license_paths() -> list[Path]:
    # Portable mode disabled — only app data dir. Keep portable check only for
    # backward compat if an old license.key was left next to the exe.
    paths: list[Path] = []
    if getattr(sys, "frozen", False):
        try:
            exe_dir = Path(sys.executable).resolve().parent
            p = exe_dir / LICENSE_FILENAME
            if p.exists():
                paths.append(p)
        except (OSError, ValueError):
            pass
    try:
        from skyadmin_pro.paths import app_data_dir

        paths.append(app_data_dir() / LICENSE_FILENAME)
    except (ImportError, OSError):
        paths.append(Path.home() / ".skyadmin_pro" / LICENSE_FILENAME)
    return paths


def find_license_file() -> Path | None:
    for p in _license_paths():
        if p.exists() and p.is_file():
            return p
    # Primary missing — try to self-heal from the shadow copy.
    healed = _self_heal_license()
    if healed is not None and healed.exists():
        return healed
    return None
