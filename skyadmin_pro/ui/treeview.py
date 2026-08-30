"""ttk.Treeview styled to follow CustomTkinter light/dark appearance."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from tkinter import ttk

import customtkinter as ctk

from skyadmin_pro.ui.theme import TABLE_FONT_SIZE, TABLE_HEADER_FONT_SIZE, TABLE_ROW_HEIGHT, table_palette


class ThemedTreeview(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        columns: Sequence[tuple[str, str, int]],
        on_select: Callable[[str | None], None] | None = None,
        on_double_click: Callable[[str | None], None] | None = None,
        showheight: int = 10,
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
            height=showheight,
        )
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.hscrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=self.hscrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.hscrollbar.grid(row=1, column=0, sticky="ew")
        # Excel-like: smooth wheel scrolling (Shift+wheel for horizontal)
        self.tree.bind("<MouseWheel>", self._on_mousewheel)
        self.tree.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.tree.bind("<Button-4>", lambda e: self.tree.yview_scroll(-1, "units"))
        self.tree.bind("<Button-5>", lambda e: self.tree.yview_scroll(1, "units"))

        self._sort_col: str | None = None
        self._sort_reverse = False
        for column_id, heading, width in columns:
            # All columns stretch + resizable like Excel — user can drag header edge to resize
            self.tree.heading(
                column_id,
                text=heading,
                anchor="w",
                command=lambda c=column_id: self._sort_by(c, False),
            )
            self.tree.column(column_id, width=width, minwidth=80, stretch=True, anchor="w")

        self.tree.bind("<<TreeviewSelect>>", self._handle_select)
        if on_double_click:
            self.tree.bind("<Double-1>", lambda _e: on_double_click(self.selected_iid()))

        self.apply_theme()

    def apply_theme(self) -> None:
        mode = ctk.get_appearance_mode()
        palette = table_palette(mode)
        background = palette["background"]
        foreground = palette["foreground"]
        heading = palette["heading"]
        selected = palette["selected"]
        odd = palette["odd"]
        even = palette["even"]
        expired = palette["expired"]
        urgent = palette["urgent"]
        watch = palette["watch"]
        green = palette["green"]
        yellow = palette["yellow"]
        orange = palette["orange"]
        red = palette["red"]
        done = palette["done"]
        wip = palette["wip"]

        # Reuse existing style to avoid memory leak from creating new Style objects
        try:
            style = ttk.Style()
            # Only set theme if not already set (avoids global side effect)
            if "clam" not in style.theme_names():
                style.theme_use("clam")
        except ttk.TclError:
            pass
        style = ttk.Style()

        style.configure(
            "Sky.Treeview",
            background=background,
            foreground=foreground,
            fieldbackground=background,
            rowheight=TABLE_ROW_HEIGHT,
            borderwidth=0,
            font=("Segoe UI", TABLE_FONT_SIZE)
            if __import__("sys").platform == "win32"
            else ("SF Pro Text", TABLE_FONT_SIZE)
            if __import__("sys").platform == "darwin"
            else ("Ubuntu", TABLE_FONT_SIZE),
        )
        style.configure(
            "Sky.Treeview.Heading",
            background=heading,
            foreground=foreground,
            relief="flat",
            font=("Segoe UI", TABLE_HEADER_FONT_SIZE, "bold")
            if __import__("sys").platform == "win32"
            else ("SF Pro Text", TABLE_HEADER_FONT_SIZE, "bold")
            if __import__("sys").platform == "darwin"
            else ("Ubuntu", TABLE_HEADER_FONT_SIZE, "bold"),
        )
        style.map("Sky.Treeview", background=[("selected", selected)])
        self.tree.configure(style="Sky.Treeview")
        self.tree.tag_configure("odd", background=odd)
        self.tree.tag_configure("even", background=even)
        self.tree.tag_configure("expired", background=expired, foreground=foreground)
        self.tree.tag_configure("urgent", background=urgent, foreground=foreground)
        self.tree.tag_configure("watch", background=watch, foreground=foreground)
        self.tree.tag_configure("green", background=green, foreground=foreground)
        self.tree.tag_configure("yellow", background=yellow, foreground=foreground)
        self.tree.tag_configure("orange", background=orange, foreground=foreground)
        self.tree.tag_configure("red", background=red, foreground=foreground)
        self.tree.tag_configure("done", background=done, foreground=foreground)
        self.tree.tag_configure("wip", background=wip, foreground=foreground)
        self.tree.tag_configure("completed", foreground=("#71717a" if mode == "Light" else "#a1a1aa"))
        self.tree.tag_configure("inactive", foreground=("#71717a" if mode == "Light" else "#a1a1aa"))

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
        # Remember the selection so a refresh doesn't lose the user's place.
        previous = self.tree.selection()
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        row_list = list(rows)
        for index, values in enumerate(row_list):
            iid = str(iids[index]) if iids is not None else str(index)
            extra = list(tags[index]) if tags is not None else []
            combined = tuple(dict.fromkeys(extra)) if extra else ("even" if index % 2 else "odd",)
            self.tree.insert("", "end", iid=iid, values=values, tags=combined)
        restored = [iid for iid in previous if self.tree.exists(iid)]
        if restored:
            # Restore silently: selection_set fires <<TreeviewSelect>>,
            # which would re-run the select handler and can loop refreshes.
            self.tree.unbind("<<TreeviewSelect>>")
            try:
                self.tree.selection_set(restored)
                self.tree.see(restored[0])
            except Exception:
                pass
            finally:
                self.tree.bind("<<TreeviewSelect>>", self._handle_select)
        elif previous and row_list:
            # Selection was cleared on purpose by a data change; notify so
            # detail panes don't show stale info.
            if self._on_select:
                self._on_select(None)

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

    # Excel-like helpers
    def _on_mousewheel(self, event) -> None:
        import sys

        if sys.platform == "darwin":
            # macOS: delta is ±1 per scroll unit
            delta = -event.delta
        else:
            # Windows: delta 120 per notch
            delta = int(-event.delta / 120) if event.delta else 0
        if delta:
            self.tree.yview_scroll(delta, "units")
        return "break"

    def _on_shift_mousewheel(self, event) -> None:
        import sys

        if sys.platform == "darwin":
            delta = -event.delta
        else:
            delta = int(-event.delta / 120) if event.delta else 0
        if delta:
            self.tree.xview_scroll(delta, "units")
        return "break"

    def _sort_by(self, col: str, reverse: bool) -> None:
        # Toggle direction if same column clicked again
        if self._sort_col == col:
            reverse = not self._sort_reverse
        self._sort_col = col
        self._sort_reverse = reverse
        try:
            col_index = self._column_ids.index(col)
        except ValueError:
            return
        # Collect (value, iid) for current rows
        rows: list[tuple[str, str]] = []
        for iid in self.tree.get_children(""):
            vals = self.tree.item(iid, "values")
            raw = vals[col_index] if col_index < len(vals) else ""
            rows.append((raw, iid))
        # Natural sort: try numeric, fallback to case-insensitive string

        def _key(pair: tuple[str, str]):
            val = pair[0]
            # Strip currency/commas for numeric sort
            try:
                cleaned = val.replace(",", "").replace("—", "").strip()
                if cleaned and cleaned.replace(".", "", 1).replace("-", "", 1).isdigit():
                    return (0, float(cleaned))
            except Exception:
                pass
            return (1, val.lower())

        rows.sort(key=_key, reverse=reverse)
        for index, (_val, iid) in enumerate(rows):
            self.tree.move(iid, "", index)
