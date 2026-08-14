"""ttk.Treeview styled to follow CustomTkinter light/dark appearance."""

from __future__ import annotations

from tkinter import ttk
from typing import Callable, Iterable, Sequence

import customtkinter as ctk


class ThemedTreeview(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        columns: Sequence[tuple[str, str, int]],
        on_select: Callable[[str | None], None] | None = None,
        on_double_click: Callable[[str | None], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_select = on_select
        self._column_ids = [column[0] for column in columns]

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self,
            columns=self._column_ids,
            show="headings",
            selectmode="browse",
        )
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        for column_id, heading, width in columns:
            self.tree.heading(column_id, text=heading, anchor="w")
            stretch = column_id in {"title", "client", "file", "notes", "destination"}
            self.tree.column(column_id, width=width, minwidth=60, stretch=stretch, anchor="w")

        self.tree.bind("<<TreeviewSelect>>", self._handle_select)
        if on_double_click:
            self.tree.bind("<Double-1>", lambda _e: on_double_click(self.selected_iid()))

        self.apply_theme()

    def apply_theme(self) -> None:
        mode = ctk.get_appearance_mode()
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except ttk.TclError:
            pass

        if mode == "Dark":
            background, foreground = "#2b2b2b", "#f4f4f5"
            heading, selected = "#333333", "#1f538d"
            odd, even = "#2b2b2b", "#333333"
            expired, urgent, watch = "#7f1d1d", "#9a3412", "#854d0e"
        else:
            background, foreground = "#ffffff", "#18181b"
            heading, selected = "#e4e4e7", "#3b8ed0"
            odd, even = "#ffffff", "#f4f4f5"
            expired, urgent, watch = "#fecaca", "#fed7aa", "#fde68a"

        style.configure(
            "Sky.Treeview",
            background=background,
            foreground=foreground,
            fieldbackground=background,
            rowheight=28,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Sky.Treeview.Heading",
            background=heading,
            foreground=foreground,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Sky.Treeview", background=[("selected", selected)])
        self.tree.configure(style="Sky.Treeview")
        self.tree.tag_configure("odd", background=odd)
        self.tree.tag_configure("even", background=even)
        self.tree.tag_configure("expired", background=expired, foreground=foreground)
        self.tree.tag_configure("urgent", background=urgent, foreground=foreground)
        self.tree.tag_configure("watch", background=watch, foreground=foreground)
        self.tree.tag_configure("completed", foreground=("#71717a" if mode == "Light" else "#a1a1aa"))

    def clear(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def set_rows(
        self,
        rows: Iterable[tuple],
        *,
        iids: Sequence[str] | None = None,
        tags: Sequence[Sequence[str]] | None = None,
    ) -> None:
        self.clear()
        row_list = list(rows)
        for index, values in enumerate(row_list):
            iid = str(iids[index]) if iids is not None else str(index)
            extra = list(tags[index]) if tags is not None else []
            stripe = "even" if index % 2 else "odd"
            combined = tuple(dict.fromkeys([stripe, *extra]))
            self.tree.insert("", "end", iid=iid, values=values, tags=combined)

    def selected_iid(self) -> str | None:
        selection = self.tree.selection()
        return str(selection[0]) if selection else None

    def selected_values(self) -> tuple | None:
        iid = self.selected_iid()
        if iid is None:
            return None
        return self.tree.item(iid, "values")

    def _handle_select(self, _event=None) -> None:
        if self._on_select:
            self._on_select(self.selected_iid())
