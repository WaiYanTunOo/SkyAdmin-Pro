"""Qt6 application shell (Phase 3): nav + lazy stacked views + status bar.

Mirrors ``ui/main_window.py`` structure (sidebar nav from config.NAV_ITEMS,
one lazily-built page per view, status bar) without importing any
CustomTkinter code. View pages are placeholders in this phase — per-view
ports land in Phase 3 follow-ups behind the same lazy seam.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from skyadmin_pro.config import (
    DEFAULT_APPEARANCE_MODE,
    NAV_ITEMS,
    SETTING_APPEARANCE_MODE,
)
from skyadmin_pro.ui import theme as tokens
from skyadmin_pro.ui.qt import theme_bridge


def _view_title(view_id: str) -> str:
    for vid, label in NAV_ITEMS:
        if vid == view_id:
            return str(label)
    return view_id


#: Phase 3 ports register here; unknown ids fall back to the placeholder
#: so the shell stays shippable mid-migration.
VIEW_MODULES: dict[str, str] = {
    "dashboard": "skyadmin_pro.ui.qt.views.dashboard",
    "database_tasks": "skyadmin_pro.ui.qt.views.database_tasks",
    "document_hub": "skyadmin_pro.ui.qt.views.document_hub",
    "office_hub": "skyadmin_pro.ui.qt.views.office_hub",
    "utilities": "skyadmin_pro.ui.qt.views.utilities",
    "settings": "skyadmin_pro.ui.qt.views.settings",
}


class QtMainWindow:
    """QMainWindow subclass created lazily (keeps module import Qt-free)."""

    def __new__(cls, *args: Any, **kwargs: Any):
        from PySide6.QtWidgets import QMainWindow

        class _Window(QMainWindow):
            def __init__(self, db=None, paths=None, appearance: str = DEFAULT_APPEARANCE_MODE) -> None:
                super().__init__()
                self.db = db
                self.paths = paths
                self.appearance = theme_bridge.normalize_mode(appearance)
                self._pages: dict[str, Any] = {}
                self._build()

            def _build(self) -> None:
                from PySide6.QtWidgets import (
                    QHBoxLayout,
                    QListWidget,
                    QListWidgetItem,
                    QStackedWidget,
                    QStatusBar,
                    QWidget,
                )

                self.setWindowTitle("SkyAdmin Pro")
                self.resize(1280, 800)

                central = QWidget()
                central.setObjectName("qt-shell-central")
                layout = QHBoxLayout(central)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)

                self._nav = QListWidget()
                self._nav.setObjectName("qt-shell-nav")
                self._nav.setFixedWidth(tokens.SIDEBAR_WIDTH)
                for view_id, label in NAV_ITEMS:
                    icon = tokens.SIDEBAR_ICONS.get(view_id, "")
                    item = QListWidgetItem(f"{icon}  {label}" if icon else str(label))
                    item.setData(0x0100, view_id)  # Qt.UserRole
                    self._nav.addItem(item)
                self._nav.currentRowChanged.connect(lambda _row: self._on_nav())
                layout.addWidget(self._nav)

                self._stack = QStackedWidget()
                layout.addWidget(self._stack, 1)
                self.setCentralWidget(central)

                self._status = QStatusBar()
                self._status.setObjectName("qt-shell-status")
                self.setStatusBar(self._status)

                self.apply_appearance(self.appearance)
                if NAV_ITEMS:
                    self._nav.setCurrentRow(0)

            def _on_nav(self) -> None:
                item = self._nav.currentItem()
                if item is None:
                    return
                self.show_view(str(item.data(0x0100)))

            def _build_page(self, view_id: str):
                module_name = VIEW_MODULES.get(view_id)
                if module_name is not None:
                    try:
                        import importlib

                        module = importlib.import_module(module_name)
                        return module.build_page(self.db, self.paths)
                    except Exception:
                        import logging

                        logging.getLogger(__name__).exception("Qt %s build failed; using placeholder", view_id)
                from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

                page = QWidget()
                box = QVBoxLayout(page)
                box.setContentsMargins(tokens.CONTENT_PAD, tokens.CONTENT_PAD, tokens.CONTENT_PAD, tokens.CONTENT_PAD)
                title = QLabel(_view_title(view_id))
                title.setObjectName("qt-shell-title")
                subtitle = QLabel("Qt port in progress — CustomTkinter view still ships.")
                subtitle.setObjectName("qt-shell-subtitle")
                subtitle.setWordWrap(True)
                box.addWidget(title)
                box.addWidget(subtitle)
                box.addStretch(1)
                return page

            def show_view(self, view_id: str) -> None:
                """Lazily build (once) and show the page for *view_id*."""
                if view_id not in self._pages:
                    self._pages[view_id] = self._build_page(view_id)
                    self._stack.addWidget(self._pages[view_id])
                self._stack.setCurrentWidget(self._pages[view_id])
                for row in range(self._nav.count()):
                    if str(self._nav.item(row).data(0x0100)) == view_id:
                        self._nav.setCurrentRow(row)
                        break
                refresh = getattr(self._pages[view_id], "refresh", None)
                if callable(refresh):
                    try:
                        refresh()
                    except Exception:
                        import logging

                        logging.getLogger(__name__).exception("Qt page refresh failed")

            def current_view(self) -> str | None:
                item = self._nav.currentItem()
                return str(item.data(0x0100)) if item is not None else None

            def set_status(self, message: str) -> None:
                self._status.showMessage(str(message), 8000)

            def apply_appearance(self, mode: str) -> dict[str, Any]:
                from PySide6.QtWidgets import QApplication

                self.appearance = theme_bridge.normalize_mode(mode)
                return theme_bridge.apply_theme(QApplication.instance(), self.appearance)

        return _Window(*args, **kwargs)


def run(db=None, paths: str | Path | None = None) -> int:
    """Create the QApplication, show the shell, run the event loop."""
    from PySide6.QtWidgets import QApplication

    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    try:
        from skyadmin_pro.ui.qt.async_bridge import _shutdown_workers

        app.aboutToQuit.connect(lambda: _shutdown_workers())
    except Exception:
        pass
    appearance = DEFAULT_APPEARANCE_MODE
    if db is not None:
        try:
            appearance = db.get_setting(SETTING_APPEARANCE_MODE) or DEFAULT_APPEARANCE_MODE
        except Exception:
            pass
    window = QtMainWindow(db=db, paths=paths, appearance=appearance)
    window.show()
    return int(app.exec())
