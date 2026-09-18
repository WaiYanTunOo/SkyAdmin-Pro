from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_TITLE_SIZE
from skyadmin_pro.ui.widgets import themed_entry, themed_scrollable_frame, themed_textbox

from ._const_0 import _SECTION_TITLES
from .funcs import _editor_font


class UtilitiesViewMixin2:
    def _render_editor(self, top: ctk.CTkToplevel) -> None:
        for items in self._editor_draft.values():
            for item in items:
                if item.get("label_entry") is not None and item.get("text_box") is not None:
                    try:
                        item["label"] = item["label_entry"].get()
                        # strip the trailing newline Text.get always appends
                        item["text"] = item["text_box"].get("1.0", "end").rstrip("\n")
                    except Exception:
                        pass
        for child in top.winfo_children():
            child.destroy()

        scroll = themed_scrollable_frame(top, corner_radius=12)
        scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 0))
        scroll.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)

        row = 0
        for section, items in self._editor_draft.items():
            title = next(title for key, title, _hint in _SECTION_TITLES if key == section)
            ctk.CTkLabel(
                scroll,
                text=title,
                font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=12, pady=(14, 4))
            row += 1
            for item in items:
                if item["removed"]:
                    continue
                label_entry, text_box = self._snippet_editor_card(scroll, row, item, top)
                item["label_entry"] = label_entry
                item["text_box"] = text_box
                row += 1
            add = ctk.CTkFrame(scroll, fg_color="transparent")
            add.grid(row=row, column=0, sticky="ew", padx=8, pady=(2, 4))
            add.grid_columnconfigure(0, weight=1)
            ctk.CTkButton(
                add,
                text="+ Add message",
                width=130,
                height=30,
                fg_color="transparent",
                border_width=1,
                command=lambda s=section: self._add_snippet_card(top, s),
            ).grid(row=0, column=0, sticky="w")
            row += 1

        ctk.CTkButton(
            top,
            text="Save changes",
            height=42,
            command=lambda: self._save_snippet_overrides(top),
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=12)

    def _snippet_editor_card(
        self, master, row: int, item: dict, top: ctk.CTkToplevel
    ) -> tuple[ctk.CTkEntry, ctk.CTkTextbox]:
        card = ctk.CTkFrame(master, corner_radius=8)
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        card.grid_columnconfigure(0, weight=1)
        label_entry = themed_entry(card, placeholder_text="Button label", font=_editor_font())
        label_entry.insert(0, item["label"])
        label_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        text_box = themed_textbox(card, height=76, wrap="word", font=_editor_font())
        text_box.insert("1.0", item["text"])
        text_box.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        card._draft_item = item
        action_text = "Reset" if item["is_default"] else "Remove"
        ctk.CTkButton(
            card,
            text=action_text,
            width=80,
            height=26,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._remove_snippet_card(card, top),
        ).grid(row=0, column=1, sticky="e", padx=(6, 10), pady=(8, 0))
        return label_entry, text_box

    def _add_snippet_card(self, top: ctk.CTkToplevel, section: str) -> None:
        item = {
            "key": None,
            "is_default": False,
            "removed": False,
            "label": "",
            "text": "",
            "label_entry": None,
            "text_box": None,
        }
        self._editor_draft[section].append(item)
        self._render_editor(top)
