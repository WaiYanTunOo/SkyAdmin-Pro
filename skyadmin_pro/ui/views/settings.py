"""Settings view — appearance, portal URL, and local paths."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import DEFAULT_PORTAL_URL, SETTING_APPEARANCE_MODE, SETTING_PORTAL_URL
from skyadmin_pro.paths import database_path
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import FeedbackLabel


class SettingsView(BaseView):
    title = "Settings"
    subtitle = "Appearance, portal URL, workspace folders, and local database location."

    def build(self) -> None:
        self.body.grid_rowconfigure(2, weight=0)
        self.body.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self.body, corner_radius=12)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text="Appearance",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 8))

        ctk.CTkLabel(card, text="Theme", anchor="w").grid(
            row=1, column=0, sticky="w", padx=20, pady=(0, 16)
        )
        self.appearance_menu = ctk.CTkOptionMenu(
            card,
            values=["Dark", "Light", "System"],
            command=self._on_appearance_change,
            width=160,
        )
        self.appearance_menu.grid(row=1, column=1, sticky="w", padx=20, pady=(0, 16))

        portal = ctk.CTkFrame(self.body, corner_radius=12)
        portal.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        portal.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            portal,
            text="Semi-auto portal uploader",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 6))
        ctk.CTkLabel(
            portal,
            text="Opened in the browser when you click Open Portal. The file path is copied for Ctrl+V.",
            wraplength=720,
            justify="left",
            text_color=("gray40", "gray70"),
            anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=20)
        ctk.CTkLabel(portal, text="Portal URL", anchor="w").grid(
            row=2, column=0, sticky="w", padx=20, pady=(12, 16)
        )
        self.portal_var = ctk.StringVar()
        ctk.CTkEntry(portal, textvariable=self.portal_var).grid(
            row=2, column=1, sticky="ew", padx=20, pady=(12, 8)
        )
        ctk.CTkButton(portal, text="Save portal URL", width=140, command=self._save_portal).grid(
            row=3, column=1, sticky="w", padx=20, pady=(0, 16)
        )

        info = ctk.CTkFrame(self.body, corner_radius=12)
        info.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        info.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            info,
            text="Local paths",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 8))

        self.workspace_value = ctk.CTkLabel(info, text="", anchor="w", wraplength=720)
        self.db_value = ctk.CTkLabel(info, text="", anchor="w", wraplength=720)
        self.clients_value = ctk.CTkLabel(info, text="", anchor="w", wraplength=720)

        ctk.CTkLabel(info, text="Workspace", anchor="w", text_color=("gray40", "gray70")).grid(
            row=1, column=0, sticky="nw", padx=20, pady=(0, 6)
        )
        self.workspace_value.grid(row=1, column=1, sticky="w", padx=20, pady=(0, 6))

        ctk.CTkLabel(info, text="Clients", anchor="w", text_color=("gray40", "gray70")).grid(
            row=2, column=0, sticky="nw", padx=20, pady=(0, 6)
        )
        self.clients_value.grid(row=2, column=1, sticky="w", padx=20, pady=(0, 6))

        ctk.CTkLabel(info, text="Database", anchor="w", text_color=("gray40", "gray70")).grid(
            row=3, column=0, sticky="nw", padx=20, pady=(0, 18)
        )
        self.db_value.grid(row=3, column=1, sticky="w", padx=20, pady=(0, 18))

        self.feedback = FeedbackLabel(self.body)
        self.feedback.grid(row=3, column=0, sticky="ew", pady=(12, 0))

    def on_show(self) -> None:
        current = ctk.get_appearance_mode()
        self.appearance_menu.set(current)
        self.workspace_value.configure(text=str(self.app.paths.root))
        self.clients_value.configure(text=str(self.app.paths.clients))
        self.db_value.configure(text=str(database_path()))
        self.portal_var.set(
            self.app.db.get_setting(SETTING_PORTAL_URL, DEFAULT_PORTAL_URL) or DEFAULT_PORTAL_URL
        )

    def _on_appearance_change(self, choice: str) -> None:
        mode = choice.lower()
        ctk.set_appearance_mode(mode)
        self.app.db.set_setting(SETTING_APPEARANCE_MODE, mode)

    def _save_portal(self) -> None:
        url = self.portal_var.get().strip() or DEFAULT_PORTAL_URL
        self.app.db.set_setting(SETTING_PORTAL_URL, url)
        self.portal_var.set(url)
        self.feedback.success("Portal URL saved.")
