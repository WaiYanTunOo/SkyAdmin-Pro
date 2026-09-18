from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import (
    APP_TAGLINE,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
)
from skyadmin_pro.ui.widgets import bind_wrap_label


class SettingsViewMixin6:
    def on_show(self) -> None:
        # Ensure the visible tab exists before refreshing its widgets.
        current = self._current_tab()
        self._ensure_panel(current)

        if "General" in self._lazy_tabs:
            current_mode = ctk.get_appearance_mode()
            self.appearance_menu.set(current_mode)
            theme = self.app.db.get_setting(SETTING_COLOR_THEME, DEFAULT_COLOR_THEME) or DEFAULT_COLOR_THEME
            try:
                self.color_theme_menu.set(theme)
            except Exception:
                pass
            self.tagline_var.set(self.app.db.get_setting("app_tagline") or APP_TAGLINE)
            saved_lang = (self.app.db.get_setting("ui_language") or "en").upper()
            try:
                self.lang_menu.set(saved_lang)
            except Exception:
                pass
            saved_zoom = self.app.db.get_setting("ui_zoom") or "100%"
            try:
                self.zoom_menu.set(saved_zoom)
            except Exception:
                pass
            self.portal_var.set(self.app.db.get_setting(SETTING_PORTAL_URL, DEFAULT_PORTAL_URL) or DEFAULT_PORTAL_URL)
            self._refresh_update_banner()

            self.workspace_var.set(str(self.app.paths.root))
            self.path_labels["Clients"].configure(text=str(self.app.paths.clients))
            self.path_labels["Suppliers"].configure(text=str(self.app.paths.suppliers))
            self.db_value.configure(text=str(self.app.db.db_file))

        if "License" in self._lazy_tabs:
            self._refresh_license_label()
            from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED

            self.data_sync_var.set((self.app.db.get_setting(SETTING_DATA_SYNC_ENABLED) or "0").strip() == "1")

        if "Business" in self._lazy_tabs:
            self.services_text.delete("1.0", "end")
            self.services_text.insert("1.0", "\n".join(self.app.db.list_service_types()))
            self._reload_checklists()
            self._load_directory_lists()
            self._refresh_pricing_services()
            self._refresh_pricing_matrix()

        if "Data & backup" in self._lazy_tabs:
            self._refresh_integrity_banner()
            self._refresh_backup_banner()

    def _path_row(self, info, *, row: int, on_open) -> ctk.CTkLabel:
        frame = ctk.CTkFrame(info, fg_color="transparent")
        frame.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        frame.grid_columnconfigure(0, weight=1)
        value = ctk.CTkLabel(frame, text="", anchor="w")
        value.grid(row=0, column=0, sticky="ew")
        bind_wrap_label(value, frame, pad=90)
        ctk.CTkButton(frame, text="Open", width=70, fg_color="transparent", border_width=1, command=on_open).grid(
            row=0, column=1, padx=(8, 0)
        )
        return value

    def _open_audit_log(self) -> None:
        from skyadmin_pro.ui.views.audit_log import AuditLogDialog

        AuditLogDialog(self.app)
