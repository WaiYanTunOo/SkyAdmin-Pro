from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.widgets import make_modal, themed_entry


class UtilitiesViewMixin8:
    def _fill_placeholders(self, snippet, tokens: list[str]) -> None:
        top = ctk.CTkToplevel(self)
        top.title("Fill placeholders")
        top.geometry(f"500x{230 + len(tokens) * 44}")
        top.transient(self.winfo_toplevel())
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text=snippet.label,
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 2))
        ctk.CTkLabel(
            top,
            text="Fill the placeholders, then copy the finished message.",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        defaults = {
            "[Month/Year]": date.today().strftime("%B %Y"),
            "[Due Date]": date.today().strftime("%d %B %Y"),
            "[Date]": date.today().strftime("%d %B %Y"),
        }
        fields = ctk.CTkFrame(top, fg_color="transparent")
        fields.grid(row=2, column=0, sticky="ew", padx=16)
        fields.grid_columnconfigure(1, weight=1)
        entries: dict[str, ctk.CTkEntry] = {}
        for row, token in enumerate(tokens):
            ctk.CTkLabel(fields, text=token, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
            entry = themed_entry(fields)
            entry.insert(0, defaults.get(token, ""))
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            entries[token] = entry

        buttons = ctk.CTkFrame(top, fg_color="transparent")
        buttons.grid(row=3, column=0, sticky="ew", padx=16, pady=(14, 16))
        ctk.CTkButton(
            buttons,
            text="Fill & copy",
            width=130,
            command=lambda: self._finish_filled(top, snippet, entries, tokens),
        ).pack(side="left")
        ctk.CTkButton(
            buttons,
            text="Copy as-is",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._finish_copy(snippet.label, snippet.text, close=top),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            buttons,
            text="Leave a field blank to remove that placeholder.",
            text_color=TEXT_MUTED,
        ).pack(side="right")

    def _finish_filled(
        self,
        top: ctk.CTkToplevel,
        snippet,
        entries: dict[str, ctk.CTkEntry],
        tokens: list[str],
    ) -> None:
        final = snippet.text
        for token in tokens:
            final = final.replace(token, entries[token].get().strip())
        try:
            top.destroy()
        except Exception:
            pass
        self._finish_copy(snippet.label, final)
