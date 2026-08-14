"""SkyAdmin Pro entry point.

Run from the project root:

    python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python main.py` without installing the package.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import customtkinter as ctk

from skyadmin_pro.config import (
    DEFAULT_APPEARANCE_MODE,
    DEFAULT_COLOR_THEME,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_WORKSPACE_ROOT,
)
from skyadmin_pro.database import Database
from skyadmin_pro.paths import WorkspacePaths, default_workspace_root
from skyadmin_pro.ui.main_window import MainWindow


def bootstrap() -> MainWindow:
    db = Database()

    appearance = db.get_setting(SETTING_APPEARANCE_MODE, DEFAULT_APPEARANCE_MODE)
    theme = db.get_setting(SETTING_COLOR_THEME, DEFAULT_COLOR_THEME)
    ctk.set_appearance_mode(appearance or DEFAULT_APPEARANCE_MODE)
    ctk.set_default_color_theme(theme or DEFAULT_COLOR_THEME)

    workspace = db.get_setting(SETTING_WORKSPACE_ROOT) or str(default_workspace_root())
    paths = WorkspacePaths(workspace)
    paths.ensure()
    db.set_setting(SETTING_WORKSPACE_ROOT, str(paths.root))

    return MainWindow(db=db, paths=paths)


def main() -> None:
    app = bootstrap()
    app.mainloop()


if __name__ == "__main__":
    main()
