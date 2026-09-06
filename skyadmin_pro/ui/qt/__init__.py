"""Qt6 shell for SkyAdmin Pro (Phase 3) — optional, CustomTkinter stays default.

The Qt surface is intentionally lazy: importing this package never imports
PySide6. Use :func:`available` to probe and :func:`launch` to run.
Select it with ``SKYADMIN_UI=qt6`` (see ``main.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def available() -> bool:
    """Return True when the Qt6 binding imports cleanly."""
    try:
        import PySide6  # noqa: F401
    except ImportError:
        return False
    return True


def launch(db, paths: Path) -> int:
    """Run the Qt shell. Returns the QApplication exit code."""
    from skyadmin_pro.ui.qt.shell import run

    return run(db=db, paths=paths)
