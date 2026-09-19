from __future__ import annotations

import json

import customtkinter as ctk

from skyadmin_pro.config import SETTING_SNIPPET_OVERRIDES
from skyadmin_pro.services.snippets import apply_snippet_overrides
from skyadmin_pro.services.translate import direction_codes
from skyadmin_pro.ui.widgets import FeedbackLabel

from ._const_0 import _SECTION_TITLES


class UtilitiesViewMixin0:
    title = "Utilities"
    subtitle = "Copy a ready message, then translate if needed. Suppliers & AP is under Finance — not here."

    def build(self) -> None:
        actions, translator = self._UtilitiesView_build_p1()
        self._UtilitiesView_build_p2(actions, translator)

    def _on_direction(self, choice: str) -> None:
        _source, target = direction_codes(choice)
        names = {"en": "English", "my": "Burmese", "th": "Thai"}
        self.output_label.configure(text=names.get(target, target))

    def _load_snippets(self) -> None:
        raw = self.app.db.get_setting(SETTING_SNIPPET_OVERRIDES)
        overrides: dict = {}
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    overrides = parsed
            except (ValueError, TypeError):
                overrides = {}
            try:
                self._sections = {
                    section: apply_snippet_overrides(section, overrides.get(section) or {})
                    for section in ("client", "supplier", "service", "checklist")
                }
            except Exception:
                # Corrupt overrides must never prevent the view from loading.
                overrides = {}
                self._sections = {
                    section: apply_snippet_overrides(section, {})
                    for section in ("client", "supplier", "service", "checklist")
                }
        else:
            self._sections = {
                section: apply_snippet_overrides(section, {})
                for section in ("client", "supplier", "service", "checklist")
            }
        self._overrides = overrides

    def _build_hub(self) -> None:
        for child in self.hub.winfo_children():
            child.destroy()

        toolbar = ctk.CTkFrame(self.hub, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        toolbar.grid_columnconfigure(0, weight=1)
        toolbar.grid_columnconfigure(1, weight=1)
        self._hub_button(toolbar, "Customize messages", self._edit_snippets).grid(
            row=0, column=0, sticky="ew", padx=(0, 4), pady=2
        )
        self._hub_button(toolbar, "History", self._show_history, outline=True).grid(
            row=0, column=1, sticky="ew", padx=(4, 0), pady=2
        )
        self._hub_button(toolbar, "Export messages", self._export_messages, outline=True).grid(
            row=1, column=0, sticky="ew", padx=(0, 4), pady=2
        )
        self._hub_button(toolbar, "Import messages", self._import_messages, outline=True).grid(
            row=1, column=1, sticky="ew", padx=(4, 0), pady=2
        )

        row = 1
        for section, title, hint in _SECTION_TITLES:
            self._section_header(self.hub, row, section, title)
            row += 1
            self._section_hint(self.hub, row, hint)
            row += 1
            columns = 2
            row = self._snippet_grid(self.hub, self._sections[section], start_row=row, columns=columns)

        self.hub_feedback = FeedbackLabel(self.hub)
        self.hub_feedback.grid(row=row, column=0, sticky="ew", padx=12, pady=(8, 16))
