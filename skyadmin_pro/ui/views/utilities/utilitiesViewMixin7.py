from __future__ import annotations

import math
import re

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED


class UtilitiesViewMixin7:
    def _section_hint(self, master, row: int, text: str) -> None:
        ctk.CTkLabel(
            master,
            text=text,
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=12, pady=(0, 8))

    def _snippet_grid(
        self,
        master: ctk.CTkScrollableFrame,
        snippets: tuple,
        *,
        start_row: int,
        columns: int,
    ) -> int:
        grid = ctk.CTkFrame(master, fg_color="transparent")
        grid.grid(row=start_row, column=0, sticky="ew", padx=12)
        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1, uniform="snip")
        for index, snippet in enumerate(snippets):
            row, column = divmod(index, columns)
            self._wrap_button(
                grid,
                snippet.label,
                lambda item=snippet: self._copy_snippet(item),
            ).grid(row=row, column=column, sticky="ew", padx=4, pady=4)
        return start_row + math.ceil(len(snippets) / columns)

    def _hub_button(self, master, text: str, command, *, outline: bool = False):
        kwargs = {"fg_color": "transparent", "border_width": 1} if outline else {}
        return self._wrap_button(master, text, command, **kwargs)

    def _wrap_button(self, master, text: str, command, **kwargs):
        # Static wraplength only. A <Configure> wraplength resize loops in update().
        button = ctk.CTkButton(master, text=text, height=60, command=command, **kwargs)
        label = getattr(button, "_text_label", None)
        if label is not None:
            label.configure(wraplength=200, justify="center")
        return button

    def _copy_snippet(self, snippet) -> None:
        tokens: list[str] = []
        seen: set[str] = set()
        for match in re.finditer(r"\[[^\[\]]+\]", snippet.text):
            token = match.group(0)
            if token not in seen:
                seen.add(token)
                tokens.append(token)
        if tokens:
            self._fill_placeholders(snippet, tokens)
            return
        self._finish_copy(snippet.label, snippet.text)
