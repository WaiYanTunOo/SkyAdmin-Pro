from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_tabview


class SettingsViewMixin0:
    title = "Settings"
    subtitle = "Appearance, license, business defaults, and local data. Not company files."

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)

        self.feedback = FeedbackLabel(self.body)
        self.feedback.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.tabs = themed_tabview(self.body, command=self._on_tab_changed)
        self.tabs.grid(row=1, column=0, sticky="nsew", pady=(0, 0))

        self._checklist_rows: list[tuple[ctk.CTkFrame, ctk.StringVar, ctk.StringVar]] = []
        self._pricing_rows: dict[str, dict] = {}
        self._selected_pricing_id: int | None = None
        self._lazy_tabs: set[str] = set()
        self._tab_scrolls: dict = {}

        for name in ("General", "License", "Business", "Data & backup"):
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_propagate(True)

        # General is the default tab — build it now; others on first visit.
        self._ensure_panel("General")

    def _current_tab(self) -> str:
        try:
            return self.tabs.get()
        except Exception:
            return "General"

    def _on_tab_changed(self) -> None:
        name = self._current_tab()
        self._ensure_panel(name)
        if name == "License":
            self._refresh_license_label()
        elif name == "Business":
            self._load_directory_lists()
            self._refresh_pricing_services()
            self._refresh_pricing_matrix()
        elif name == "Data & backup":
            self._refresh_backup_banner()

    def _on_zoom_change(self, value: str) -> None:
        import customtkinter as ctk

        self.app.db.set_setting("ui_zoom", value)
        scale_str = value.replace("%", "")
        try:
            scale = int(scale_str) / 100.0
            ctk.set_widget_scaling(scale)
            # Re-apply theme bounds safely if possible
            self.app.apply_app_theme()
            self.app.set_status(f"UI Zoom set to {value}")
        except Exception:
            pass

    def _ensure_panel(self, name: str) -> None:
        if name in self._lazy_tabs:
            return
        tab = self.tabs.tab(name)
        if name == "General":
            self._build_general_tab(tab)
        elif name == "License":
            self._build_license_tab(tab)
        elif name == "Business":
            self._build_business_tab(tab)
        elif name == "Data & backup":
            self._build_data_tab(tab)
        else:
            return
        self._lazy_tabs.add(name)

    def _scroll_tab(self, tab) -> ctk.CTkFrame:
        scroll = CanvasScrollFrame(tab)
        scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        scroll.content.grid_columnconfigure(0, weight=1)
        scroll.content.grid_rowconfigure(0, weight=1)
        self._tab_scrolls[tab] = scroll
        return scroll.content

    def _reconfigure_tab_scroll(self, tab) -> None:
        scroll = self._tab_scrolls.get(tab)
        if scroll and hasattr(scroll, "_on_content_configure"):
            scroll._on_content_configure()

    def _build_general_tab(self, tab) -> None:
        scroll = self._scroll_tab(tab)
        row = 0
        row = self._build_general_tab_update(scroll, row)
        row = self._build_general_tab_appearance(scroll, row)
        row = self._build_general_tab_paths(scroll, row)
        row = self._build_general_tab_portal(scroll, row)
        row = self._build_general_tab_disclaimer(scroll, row)
