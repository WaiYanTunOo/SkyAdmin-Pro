from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.services.snippets import SNIPPET_SECTIONS
from skyadmin_pro.ui.widgets import make_modal

from ._const_0 import _SECTION_TITLES


class UtilitiesViewMixin1:
    def _edit_snippets(self, section: str | None = None) -> None:
        top = ctk.CTkToplevel(self)
        top.title("Customize messages")
        top.geometry("820x680")
        top.transient(self.winfo_toplevel())
        make_modal(top)

        scope = (section,) if section else tuple(key for key, _title, _hint in _SECTION_TITLES)
        self._editor_draft: dict[str, list[dict]] = {}
        for current in scope:
            defaults = SNIPPET_SECTIONS.get(current, ())
            default_labels = {snippet.label for snippet in defaults}
            section_overrides = self._overrides.get(current) or {}
            extras = sorted(
                ((key, value) for key, value in section_overrides.items() if key not in default_labels),
                key=lambda kv: (kv[1].get("label") or kv[0]).lower(),
            )
            items: list[dict] = []
            for snippet in defaults:
                items.append(
                    {
                        "key": snippet.label,
                        "is_default": True,
                        "removed": False,
                        "label": snippet.label,
                        "text": snippet.text,
                        "label_entry": None,
                        "text_box": None,
                    }
                )
            for key, value in extras:
                items.append(
                    {
                        "key": key,
                        "is_default": False,
                        "removed": False,
                        "label": value.get("label") or key,
                        "text": value.get("text") or "",
                        "label_entry": None,
                        "text_box": None,
                    }
                )
            self._editor_draft[current] = items
        self._render_editor(top)
