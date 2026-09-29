from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import SectionCard, bind_wrap_label, themed_entry


class SettingsViewMixin1:
    def _build_general_tab_update(self, scroll, row: int) -> int:
        self.update_frame = ctk.CTkFrame(scroll, corner_radius=12, fg_color=("#dbeafe", "#1e3a5f"))
        self.update_frame.grid_columnconfigure(0, weight=1)
        self.update_label = ctk.CTkLabel(self.update_frame, text="", anchor="w", justify="left")
        self.update_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        bind_wrap_label(self.update_label, self.update_frame, pad=32)
        self._update_download_btn = ctk.CTkButton(
            self.update_frame,
            text="Download",
            width=120,
            command=self._open_update_url,
        )
        self._update_download_btn.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        self.update_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        self.update_frame.grid_remove()
        return row + 1

    def _build_general_tab_appearance(self, scroll, row: int) -> int:
        appearance = SectionCard(
            scroll,
            title="Appearance",
            subtitle="Theme, accent color, sidebar tagline, and UI language.",
        )
        appearance.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        body = appearance.body
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(body, text="Theme", anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        self.appearance_menu = ctk.CTkOptionMenu(
            body,
            values=["Dark", "Light", "System"],
            command=self._on_appearance_change,
            width=160,
        )
        self.appearance_menu.grid(row=0, column=1, sticky="w", pady=4)

        ctk.CTkLabel(body, text="Accent", anchor="w").grid(row=1, column=0, sticky="w", pady=4)
        self.color_theme_menu = ctk.CTkOptionMenu(
            body,
            values=["blue", "green", "dark-blue"],
            command=self._on_color_theme_change,
            width=160,
        )
        self.color_theme_menu.grid(row=1, column=1, sticky="w", pady=4)

        ctk.CTkLabel(body, text="Tagline", anchor="w").grid(row=2, column=0, sticky="nw", pady=4)
        tag_row = ctk.CTkFrame(body, fg_color="transparent")
        tag_row.grid(row=2, column=1, sticky="ew", pady=4)
        tag_row.grid_columnconfigure(0, weight=1)
        self.tagline_var = ctk.StringVar()
        themed_entry(tag_row, textvariable=self.tagline_var).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(tag_row, text="Save", width=70, command=self._save_tagline).grid(row=0, column=1, padx=(8, 0))

        ctk.CTkLabel(body, text="Language", anchor="w").grid(row=3, column=0, sticky="w", pady=4)
        from skyadmin_pro.services.i18n import available_languages

        self.lang_menu = ctk.CTkOptionMenu(
            body,
            values=[lang.upper() for lang in available_languages()],
            command=self._on_language_change,
            width=120,
        )
        self.lang_menu.grid(row=3, column=1, sticky="w", pady=4)

        ctk.CTkLabel(body, text="UI Zoom", anchor="w").grid(row=4, column=0, sticky="w", pady=4)
        self.zoom_menu = ctk.CTkOptionMenu(
            body,
            values=["100%", "110%", "125%", "150%", "175%", "200%"],
            command=self._on_zoom_change,
            width=160,
        )
        self.zoom_menu.grid(row=4, column=1, sticky="w", pady=4)

        ctk.CTkLabel(
            body,
            text="Shortcuts:  Ctrl+F / Ctrl+K Magic Search   ·   Ctrl+E export   ·   "
            "Ctrl+N new client   ·   Ctrl+S save   ·   Ctrl+Z undo   ·   Ctrl+D theme",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
        ).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        return row + 1

    def _build_general_tab_paths(self, scroll, row: int) -> int:
        info = self._SettingsView_build_general_tab_paths_p1(scroll, row)
        self._SettingsView_build_general_tab_paths_p2(info)
        return row + 1
