"""Main application window: sidebar navigation + swapping content frames."""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from skyadmin_pro.config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    DEFAULT_WINDOW_GEOMETRY,
    MIN_WINDOW_SIZE,
    NAV_DASHBOARD,
    NAV_ITEMS,
    SETTING_WINDOW_GEOMETRY,
)
from skyadmin_pro.ui.dnd import dnd_base_class, init_dnd
from skyadmin_pro.ui.theme import SIDEBAR_BUTTON_HEIGHT, SIDEBAR_PADX, SIDEBAR_PADY, SIDEBAR_WIDTH
from skyadmin_pro.ui.views.dashboard import DashboardView
from skyadmin_pro.ui.views.database_tasks import DatabaseTasksView
from skyadmin_pro.ui.views.document_hub import DocumentHubView
from skyadmin_pro.ui.views.settings import SettingsView
from skyadmin_pro.ui.views.utilities import UtilitiesView

if TYPE_CHECKING:
    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths


class MainWindow(dnd_base_class()):
    def __init__(self, db: Database, paths: WorkspacePaths) -> None:
        super().__init__()
        self.db = db
        self.paths = paths
        self.dnd_available = init_dnd(self)

        self.title(APP_NAME)
        geometry = self.db.get_setting(SETTING_WINDOW_GEOMETRY, DEFAULT_WINDOW_GEOMETRY)
        self.geometry(geometry or DEFAULT_WINDOW_GEOMETRY)
        self.minsize(*MIN_WINDOW_SIZE)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._views: dict[str, ctk.CTkFrame] = {}
        self._active_key: str | None = None

        self._build_sidebar()
        self._build_content()
        self._build_status_bar()
        self.show_view(NAV_DASHBOARD)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self, width=SIDEBAR_WIDTH, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(len(NAV_ITEMS) + 2, weight=1)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=SIDEBAR_PADX, pady=(24, 20))

        ctk.CTkLabel(
            brand,
            text=APP_NAME,
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            brand,
            text=APP_TAGLINE,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        for index, (key, label) in enumerate(NAV_ITEMS, start=1):
            button = ctk.CTkButton(
                self.sidebar,
                text=label,
                height=SIDEBAR_BUTTON_HEIGHT,
                corner_radius=8,
                anchor="w",
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                command=lambda k=key: self.show_view(k),
            )
            button.grid(row=index, column=0, sticky="ew", padx=SIDEBAR_PADX, pady=SIDEBAR_PADY)
            self._nav_buttons[key] = button

        ctk.CTkLabel(
            self.sidebar,
            text=f"v{APP_VERSION}  ·  Offline",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        ).grid(row=len(NAV_ITEMS) + 3, column=0, padx=SIDEBAR_PADX, pady=(0, 18), sticky="sw")

    def _build_content(self) -> None:
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        view_classes = {
            "dashboard": DashboardView,
            "document_hub": DocumentHubView,
            "database_tasks": DatabaseTasksView,
            "utilities": UtilitiesView,
            "settings": SettingsView,
        }
        for key, view_cls in view_classes.items():
            view = view_cls(self.content, app=self)
            view.grid(row=0, column=0, sticky="nsew")
            self._views[key] = view

    def _build_status_bar(self) -> None:
        self.status_bar = ctk.CTkFrame(self, height=32, corner_radius=0)
        self.status_bar.grid(row=1, column=1, sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text=f"Workspace: {self.paths.root}",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray70"),
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=16, pady=6)

        db_ok = "Database ready" if self.db.ping() else "Database error"
        ctk.CTkLabel(
            self.status_bar,
            text=db_ok,
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray70"),
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=16, pady=6)

    def show_view(self, key: str) -> None:
        if key not in self._views:
            return

        if self._active_key and self._active_key != key:
            on_hide = getattr(self._views[self._active_key], "on_hide", None)
            if callable(on_hide):
                on_hide()

        self._views[key].tkraise()
        self._active_key = key
        self._highlight_nav(key)

        on_show = getattr(self._views[key], "on_show", None)
        if callable(on_show):
            on_show()

    def _highlight_nav(self, active_key: str) -> None:
        for key, button in self._nav_buttons.items():
            if key == active_key:
                button.configure(fg_color=("gray75", "gray30"))
            else:
                button.configure(fg_color="transparent")

    def set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def _on_close(self) -> None:
        self.db.set_setting(SETTING_WINDOW_GEOMETRY, self.geometry())
        self.destroy()
