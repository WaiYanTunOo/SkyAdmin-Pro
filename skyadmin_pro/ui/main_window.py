"""Main application window: sidebar navigation + swapping content frames."""

from __future__ import annotations

from collections.abc import Callable
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
    NAV_OFFICE_HUB,
    SETTING_SIDEBAR_COLLAPSED,
    SETTING_WINDOW_GEOMETRY,
)
from skyadmin_pro.services.i18n import tr
from skyadmin_pro.ui.dnd import dnd_base_class, init_dnd
from skyadmin_pro.ui.theme import (
    SIDEBAR_ACTIVE_BG,
    SIDEBAR_ACTIVE_TEXT,
    SIDEBAR_BUTTON_HEIGHT,
    SIDEBAR_COLLAPSED_WIDTH,
    SIDEBAR_HOVER_BG,
    SIDEBAR_ICONS,
    SIDEBAR_PADX,
    SIDEBAR_PADY,
    SIDEBAR_TEXT,
    SIDEBAR_WIDTH,
    STATUS_BAR_HEIGHT,
    TEXT_FAINT,
    TEXT_MUTED,
)

if TYPE_CHECKING:
    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths
    from skyadmin_pro.ui.views.base import BaseView


class MainWindow(dnd_base_class()):
    _VIEW_FACTORIES: dict[str, Callable[[MainWindow], BaseView]] = {}

    @classmethod
    def _register_view_factories(cls) -> None:
        if cls._VIEW_FACTORIES:
            return
        from skyadmin_pro.ui.views.dashboard import DashboardView
        from skyadmin_pro.ui.views.database_tasks import DatabaseTasksView
        from skyadmin_pro.ui.views.document_hub import DocumentHubView
        from skyadmin_pro.ui.views.office_hub import OfficeHubView
        from skyadmin_pro.ui.views.settings import SettingsView
        from skyadmin_pro.ui.views.utilities import UtilitiesView

        cls._VIEW_FACTORIES = {
            "dashboard": lambda app: DashboardView(app.content, app=app),
            "document_hub": lambda app: DocumentHubView(app.content, app=app),
            "database_tasks": lambda app: DatabaseTasksView(app.content, app=app),
            "office_hub": lambda app: OfficeHubView(app.content, app=app),
            "utilities": lambda app: UtilitiesView(app.content, app=app),
            "settings": lambda app: SettingsView(app.content, app=app),
        }

    def __init__(self, db: Database, paths: WorkspacePaths) -> None:
        super().__init__()
        self.db = db
        self.paths = paths
        self.dnd_available = init_dnd(self)
        self._register_view_factories()

        self.title(APP_NAME)
        geometry = self.db.get_setting(SETTING_WINDOW_GEOMETRY, DEFAULT_WINDOW_GEOMETRY)
        self.geometry(geometry or DEFAULT_WINDOW_GEOMETRY)
        self.minsize(*MIN_WINDOW_SIZE)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._nav_labels: dict[str, str] = dict(NAV_ITEMS)
        self._views: dict[str, ctk.CTkFrame] = {}
        self._active_key: str | None = None
        self._sidebar_collapsed = self.db.get_setting(SETTING_SIDEBAR_COLLAPSED) == "1"

        self._build_sidebar()
        self._build_content()
        self._build_status_bar()
        self.show_view(NAV_DASHBOARD)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_sidebar(self) -> None:
        # Plain logical width — CustomTkinter scales it for Windows DPI itself;
        # do NOT multiply again here or the sidebar balloons at high scale.
        width = SIDEBAR_COLLAPSED_WIDTH if self._sidebar_collapsed else SIDEBAR_WIDTH
        self.sidebar = ctk.CTkFrame(self, width=width, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(len(NAV_ITEMS) + 2, weight=1)

        top_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", padx=8, pady=(12, 4))
        top_row.grid_columnconfigure(0, weight=1)

        self.sidebar_toggle_btn = ctk.CTkButton(
            top_row,
            text="»" if self._sidebar_collapsed else "«",
            width=36,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            hover_color=SIDEBAR_HOVER_BG,
            command=self._toggle_sidebar,
        )
        self.sidebar_toggle_btn.grid(row=0, column=0, sticky="e")

        self.brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.brand.grid(row=1, column=0, sticky="ew", padx=SIDEBAR_PADX, pady=(0, 16))

        ctk.CTkLabel(
            self.brand,
            text=APP_NAME,
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        self.tagline_label = ctk.CTkLabel(
            self.brand,
            text=self.db.get_setting("app_tagline") or APP_TAGLINE,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.tagline_label.pack(fill="x", pady=(2, 0))

        for index, (key, label) in enumerate(NAV_ITEMS, start=2):
            icon = SIDEBAR_ICONS.get(key, "•")
            button_text = icon if self._sidebar_collapsed else f"{icon}  {tr(label)}"

            button = ctk.CTkButton(
                self.sidebar,
                text=button_text,
                height=SIDEBAR_BUTTON_HEIGHT,
                corner_radius=10,
                anchor="center" if self._sidebar_collapsed else "w",
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                text_color=SIDEBAR_TEXT,
                hover_color=SIDEBAR_HOVER_BG,
                command=lambda k=key: self.show_view(k),
            )
            padx = 8 if self._sidebar_collapsed else SIDEBAR_PADX
            button.grid(row=index, column=0, sticky="ew", padx=padx, pady=SIDEBAR_PADY)
            self._nav_buttons[key] = button

        self.version_label = ctk.CTkLabel(
            self.sidebar,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_FAINT,
        )
        self.version_label.grid(row=len(NAV_ITEMS) + 3, column=0, padx=SIDEBAR_PADX, pady=(0, 2), sticky="sw")
        self.refresh_sidebar_status()
        self.copyright_label = ctk.CTkLabel(
            self.sidebar,
            text="© Sky Creation Innovations\nAll rights reserved",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_FAINT,
            justify="left",
            anchor="w",
        )
        self.copyright_label.grid(row=len(NAV_ITEMS) + 4, column=0, padx=SIDEBAR_PADX, pady=(0, 18), sticky="sw")
        self._apply_sidebar_layout()

    def _toggle_sidebar(self) -> None:
        self._sidebar_collapsed = not self._sidebar_collapsed
        self.db.set_setting(SETTING_SIDEBAR_COLLAPSED, "1" if self._sidebar_collapsed else "0")
        self._apply_sidebar_layout()

    def _apply_sidebar_layout(self) -> None:
        collapsed = self._sidebar_collapsed
        width = SIDEBAR_COLLAPSED_WIDTH if collapsed else SIDEBAR_WIDTH
        self.sidebar.configure(width=width)
        self.sidebar_toggle_btn.configure(text="»" if collapsed else "«")

        if collapsed:
            self.brand.grid_remove()
            self.version_label.grid_remove()
            self.copyright_label.grid_remove()
        else:
            self.brand.grid()
            self.version_label.grid()
            self.copyright_label.grid()

        for key, button in self._nav_buttons.items():
            icon = SIDEBAR_ICONS.get(key, "•")
            if collapsed:
                button.configure(text=icon, anchor="center")
                button.grid_configure(padx=8)
            else:
                button.configure(text=f"{icon}  {tr(self._nav_labels[key])}", anchor="w")
                button.grid_configure(padx=SIDEBAR_PADX)

    def _get_window_scaling(self) -> float:
        """Pixels-per-point reported by Tk (diagnostic use only)."""
        try:
            return float(self.tk.call("tk", "scaling"))
        except Exception:
            return 1.0

    def _build_content(self) -> None:
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _ensure_view(self, key: str) -> ctk.CTkFrame | None:
        if key in self._views:
            return self._views[key]
        factory = self._VIEW_FACTORIES.get(key)
        if factory is None:
            return None
        view = factory(self)
        view.grid(row=0, column=0, sticky="nsew")
        self._views[key] = view
        return view

    def _build_status_bar(self) -> None:
        self.status_bar = ctk.CTkFrame(self, height=STATUS_BAR_HEIGHT, corner_radius=0)
        self.status_bar.grid(row=1, column=1, sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)
        # Let text dictate height at high DPI instead of clipping.
        self.status_bar.grid_propagate(False)
        self.status_bar.grid_rowconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text=f"Workspace: {self.paths.root}",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=16, pady=6)
        from skyadmin_pro.ui.widgets import bind_wrap_label

        bind_wrap_label(self.status_label, self.status_bar, pad=180)

        db_ok = "Database ready" if self.db.ping() else "Database error"
        ctk.CTkLabel(
            self.status_bar,
            text=db_ok,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=16, pady=6)

    def show_view(self, key: str) -> None:
        view = self._ensure_view(key)
        if view is None:
            return

        if self._active_key and self._active_key != key:
            on_hide = getattr(self._views[self._active_key], "on_hide", None)
            if callable(on_hide):
                on_hide()

        view.tkraise()
        self._active_key = key
        self._highlight_nav(key)

        on_show = getattr(view, "on_show", None)
        if callable(on_show):
            on_show()
        self.apply_app_theme(view)

    def apply_app_theme(self, root: ctk.Misc | None = None) -> None:
        """Re-apply form input and table styling after appearance changes."""
        from skyadmin_pro.ui.widgets import apply_form_theme

        if root is not None:
            apply_form_theme(root)
            return
        apply_form_theme(self)
        for view in self._views.values():
            apply_form_theme(view)

    def open_office_hub_client_credentials(
        self,
        client_name: str,
        *,
        credential_type: str | None = None,
        credential_id: int | None = None,
    ) -> None:
        """Navigate to Office Hub → Client DBD/RD for the given company."""
        view = self._ensure_view(NAV_OFFICE_HUB)
        if view is not None:
            view._pending_client_credentials = (
                (client_name or "").strip(),
                credential_type,
                credential_id,
            )
        self.show_view(NAV_OFFICE_HUB)

    def open_office_hub_client_rd(self, client_name: str) -> None:
        """Backward-compatible alias for RD-only navigation."""
        self.open_office_hub_client_credentials(client_name, credential_type="RD")

    def open_accounting_setup(self) -> None:
        """Navigate to Company Details → Accounting Setup rollout queue."""
        from skyadmin_pro.config import NAV_DATABASE_TASKS

        view = self._ensure_view(NAV_DATABASE_TASKS)
        if view is not None and hasattr(view, "open_accounting_setup"):
            view.open_accounting_setup()
        self.show_view(NAV_DATABASE_TASKS)

    def open_office_hub_setup(self) -> None:
        """Navigate to Office Hub → Setup migration queue."""
        view = self._ensure_view(NAV_OFFICE_HUB)
        if view is not None and hasattr(view, "open_setup"):
            view.open_setup()
        self.show_view(NAV_OFFICE_HUB)

    def open_vo_csh_setup(self) -> None:
        """Navigate to Company Details → VO/CSH Setup rollout queue."""
        from skyadmin_pro.config import NAV_DATABASE_TASKS

        view = self._ensure_view(NAV_DATABASE_TASKS)
        if view is not None and hasattr(view, "open_vo_csh_setup"):
            view.open_vo_csh_setup()
        self.show_view(NAV_DATABASE_TASKS)

    def _highlight_nav(self, active_key: str) -> None:
        for key, button in self._nav_buttons.items():
            if key == active_key:
                button.configure(
                    fg_color=SIDEBAR_ACTIVE_BG, text_color=SIDEBAR_ACTIVE_TEXT, hover_color=SIDEBAR_ACTIVE_BG
                )
            else:
                button.configure(fg_color="transparent", text_color=SIDEBAR_TEXT, hover_color=SIDEBAR_HOVER_BG)

    def refresh_sidebar_status(self) -> None:
        """Update sidebar version line (license expiry when active)."""
        from skyadmin_pro.services.license import (
            available_update,
            license_expiry_text,
            verify_license,
        )

        update = available_update()
        if update:
            ver = update.get("version", "?")
            self.version_label.configure(text=f"v{APP_VERSION}  ·  Update: v{ver}")
            return

        ok, _msg = verify_license()
        if ok:
            expiry = license_expiry_text()
            if expiry.startswith("no expiry"):
                self.version_label.configure(text=f"v{APP_VERSION}  ·  Licensed")
            else:
                self.version_label.configure(text=f"v{APP_VERSION}  ·  {expiry}")
        else:
            self.version_label.configure(text=f"v{APP_VERSION}")

    def refresh_tagline(self, text: str | None = None) -> None:
        from skyadmin_pro.config import APP_TAGLINE

        self.tagline_label.configure(text=text or self.db.get_setting("app_tagline") or APP_TAGLINE)

    def set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def _on_close(self) -> None:
        # Give the active view a chance to cancel polling / after handles so
        # callbacks don't fire on a destroyed widget.
        if self._active_key and self._active_key in self._views:
            on_hide = getattr(self._views[self._active_key], "on_hide", None)
            if callable(on_hide):
                try:
                    on_hide()
                except Exception:
                    pass
        for view in self._views.values():
            teardown = getattr(view, "on_hide", None)
            if callable(teardown):
                try:
                    teardown()
                except Exception:
                    pass
        self.db.set_setting(SETTING_WINDOW_GEOMETRY, self.geometry())
        self.destroy()
