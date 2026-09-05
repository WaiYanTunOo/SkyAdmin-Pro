"""ttk.Treeview styled to follow CustomTkinter light/dark appearance."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable, Sequence
from tkinter import ttk

import customtkinter as ctk

from skyadmin_pro.ui.theme import TABLE_FONT_SIZE, TABLE_HEADER_FONT_SIZE, TABLE_ROW_HEIGHT, table_palette

_VIRTUAL_THRESHOLD = 60
_INCREMENTAL_THRESHOLD = 20


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
        self._showheight = showheight
        self._virtual_active = False
        self._virtual_offset = 0
        self._virtual_rows: list[tuple] = []
        self._virtual_iids: list[str] = []
        self._virtual_tags: list[tuple[str, ...]] | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self,
            columns=self._column_ids,
            show="headings",
            selectmode="browse",
            height=showheight,
        )
        self._vscroll = ttk.Scrollbar(
            self, orient="vertical", command=self._scrollbar_command, style="Sky.Vertical.TScrollbar"
        )
        self.hscrollbar = ttk.Scrollbar(
            self, orient="horizontal", command=self.tree.xview, style="Sky.Horizontal.TScrollbar"
        )
        self.tree.configure(yscrollcommand=self._yscroll_command, xscrollcommand=self.hscrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self._vscroll.grid(row=0, column=1, sticky="ns")
        self.hscrollbar.grid(row=1, column=0, sticky="ew")
        # Excel-like: smooth wheel scrolling (Shift+wheel for horizontal)
        self.tree.bind("<MouseWheel>", self._on_mousewheel)
        self.tree.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.tree.bind("<Button-4>", lambda _e: self._scroll_vertical(-1))
        self.tree.bind("<Button-5>", lambda _e: self._scroll_vertical(1))

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
        heading_fg = palette.get("heading_fg", foreground)
        field_bg = palette.get("fieldbackground", background)
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
        scrollbar = palette.get("scrollbar", "#4b5563")
        trough = palette.get("trough", background)

        self.configure(fg_color=background)

        style = ttk.Style()
        try:
            if style.theme_use() != "clam":
                style.theme_use("clam")
        except ttk.TclError:
            try:
                style.theme_use("clam")
            except ttk.TclError:
                pass
        # Scale rowheight/font for Windows high-DPI (ctk scaling)
        try:
            scale = float(self.tk.call("tk", "scaling"))
        except Exception:
            scale = 1.0
        # Clamp scale to reasonable range (1.0-1.5)
        scale = max(1.0, min(1.5, scale))
        scaled_row = int(TABLE_ROW_HEIGHT * scale)
        scaled_font = int(TABLE_FONT_SIZE * scale)
        scaled_head = int(TABLE_HEADER_FONT_SIZE * scale)

        style.configure(
            "Sky.Treeview",
            background=background,
            foreground=foreground,
            fieldbackground=field_bg,
            rowheight=scaled_row,
            borderwidth=0,
            font=("Segoe UI", scaled_font)
            if sys.platform == "win32"
            else ("SF Pro Text", scaled_font)
            if sys.platform == "darwin"
            else ("Ubuntu", scaled_font),
        )
        style.configure(
            "Sky.Treeview.Heading",
            background=heading,
            foreground=heading_fg,
            fieldbackground=heading,
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", scaled_head, "bold")
            if sys.platform == "win32"
            else ("SF Pro Text", scaled_head, "bold")
            if sys.platform == "darwin"
            else ("Ubuntu", scaled_head, "bold"),
        )
        style.map(
            "Sky.Treeview",
            background=[("selected", selected)],
            foreground=[("selected", "#ffffff")],
        )
        style.map(
            "Sky.Treeview.Heading",
            background=[("active", heading), ("!active", heading)],
            foreground=[("active", heading_fg), ("!active", heading_fg)],
            relief=[("active", "flat"), ("!active", "flat")],
        )
        style.configure(
            "Sky.Vertical.TScrollbar",
            background=scrollbar,
            troughcolor=trough,
            borderwidth=0,
            arrowcolor=foreground,
        )
        style.configure(
            "Sky.Horizontal.TScrollbar",
            background=scrollbar,
            troughcolor=trough,
            borderwidth=0,
            arrowcolor=foreground,
        )
        style.map(
            "Sky.Vertical.TScrollbar",
            background=[("active", scrollbar), ("!active", scrollbar)],
        )
        style.map(
            "Sky.Horizontal.TScrollbar",
            background=[("active", scrollbar), ("!active", scrollbar)],
        )
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
        self.tree.tag_configure("empty", foreground=("#71717a" if mode == "Light" else "#a1a1aa"))

    def clear(self) -> None:
        self._deactivate_virtual()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def set_rows(
        self,
        rows: Iterable[tuple],
        *,
        iids: Sequence[str] | None = None,
        tags: Sequence[Sequence[str]] | None = None,
        empty_message: str | None = None,
    ) -> None:
        row_list = list(rows)
        if not row_list and empty_message:
            width = max(1, len(self._column_ids))
            row_list = [(empty_message,) + ("",) * (width - 1)]
            iids = ["__empty__"]
            tags = [("empty",)]
        if iids is not None and len(row_list) >= _VIRTUAL_THRESHOLD:
            self._set_rows_virtual(row_list, iids=iids, tags=tags)
            return

        self._deactivate_virtual()
        if iids is not None and len(row_list) > _INCREMENTAL_THRESHOLD:
            self._set_rows_incremental(row_list, iids=iids, tags=tags)
            return

        # Remember the selection so a refresh doesn't lose the user's place.
        previous = self.tree.selection()
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        for index, values in enumerate(row_list):
            iid = str(iids[index]) if iids is not None else str(index)
            extra = list(tags[index]) if tags is not None else []
            combined = tuple(dict.fromkeys(extra)) if extra else ("even" if index % 2 else "odd",)
            self.tree.insert("", "end", iid=iid, values=values, tags=combined)
        self._restore_selection(previous, row_list)

    def _row_tags(self, index: int, tags: Sequence[Sequence[str]] | None) -> tuple[str, ...]:
        extra = list(tags[index]) if tags is not None else []
        return tuple(dict.fromkeys(extra)) if extra else ("even" if index % 2 else "odd",)

    def _deactivate_virtual(self) -> None:
        self._virtual_active = False
        self._virtual_offset = 0
        self._virtual_rows = []
        self._virtual_iids = []
        self._virtual_tags = None

    def _visible_row_count(self) -> int:
        return max(1, int(self.tree.cget("height")))

    def _set_rows_virtual(
        self,
        row_list: list[tuple],
        *,
        iids: Sequence[str],
        tags: Sequence[Sequence[str]] | None,
    ) -> None:
        previous = tuple(self.tree.selection())
        selected = str(previous[0]) if previous else None
        self._virtual_active = True
        self._virtual_rows = row_list
        self._virtual_iids = [str(i) for i in iids]
        self._virtual_tags = (
            [self._row_tags(index, tags) for index in range(len(row_list))] if tags is not None else None
        )
        if selected and selected in self._virtual_iids:
            index = self._virtual_iids.index(selected)
            visible = self._visible_row_count()
            self._virtual_offset = max(0, min(index, max(0, len(row_list) - visible)))
        else:
            self._virtual_offset = min(self._virtual_offset, max(0, len(row_list) - self._visible_row_count()))
        self._render_virtual_window()
        self._restore_selection(previous, row_list)

    def _render_virtual_window(self) -> None:
        total = len(self._virtual_rows)
        visible = self._visible_row_count()
        start = min(self._virtual_offset, max(0, total - visible))
        self._virtual_offset = start
        end = min(start + visible, total)

        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        for index in range(start, end):
            iid = self._virtual_iids[index]
            tag_values = self._virtual_tags[index] if self._virtual_tags is not None else self._row_tags(index, None)
            self.tree.insert("", "end", iid=iid, values=self._virtual_rows[index], tags=tag_values)
        self._update_virtual_scrollbar()

    def _update_virtual_scrollbar(self) -> None:
        total = len(self._virtual_rows)
        visible = self._visible_row_count()
        if total <= visible:
            self._vscroll.set(0.0, 1.0)
            return
        first = self._virtual_offset / total
        last = (self._virtual_offset + visible) / total
        self._vscroll.set(first, last)

    def _virtual_scroll_to_fraction(self, fraction: float) -> None:
        total = len(self._virtual_rows)
        visible = self._visible_row_count()
        max_offset = max(0, total - visible)
        self._virtual_offset = int(max(0.0, min(1.0, fraction)) * max_offset)
        self._render_virtual_window()

    def _virtual_scroll_by_units(self, count: int, units: str) -> None:
        total = len(self._virtual_rows)
        visible = self._visible_row_count()
        step = count if units == "units" else count * visible
        max_offset = max(0, total - visible)
        self._virtual_offset = max(0, min(max_offset, self._virtual_offset + step))
        self._render_virtual_window()

    def _scrollbar_command(self, *args) -> None:
        if self._virtual_active and args:
            if args[0] == "moveto":
                self._virtual_scroll_to_fraction(float(args[1]))
                return
            if args[0] == "scroll":
                self._virtual_scroll_by_units(int(args[1]), args[2])
                return
        self.tree.yview(*args)

    def _yscroll_command(self, first, last) -> None:
        if not self._virtual_active:
            self._vscroll.set(first, last)

    def _set_rows_incremental(
        self,
        row_list: list[tuple],
        *,
        iids: Sequence[str],
        tags: Sequence[Sequence[str]] | None,
    ) -> None:
        previous = self.tree.selection()
        new_ids = {str(iids[index]) for index in range(len(row_list))}
        for iid in self.tree.get_children():
            if str(iid) not in new_ids:
                self.tree.delete(iid)
        for index, values in enumerate(row_list):
            iid = str(iids[index])
            extra = list(tags[index]) if tags is not None else []
            combined = tuple(dict.fromkeys(extra)) if extra else ("even" if index % 2 else "odd",)
            if self.tree.exists(iid):
                if tuple(self.tree.item(iid, "values")) != tuple(values):
                    self.tree.item(iid, values=values, tags=combined)
            else:
                self.tree.insert("", "end", iid=iid, values=values, tags=combined)
        self._restore_selection(previous, row_list)

    def _restore_selection(self, previous: tuple, row_list: list[tuple]) -> None:
        restored = [iid for iid in previous if self.tree.exists(iid)]
        if restored:
            self.tree.unbind("<<TreeviewSelect>>")
            try:
                self.tree.selection_set(restored)
                self.tree.see(restored[0])
            except Exception:
                pass
            finally:
                self.tree.bind("<<TreeviewSelect>>", self._handle_select)
        elif previous and row_list:
            if self._on_select:
                self._on_select(None)

    def selected_iid(self) -> str | None:
        selection = self.tree.selection()
        return str(selection[0]) if selection else None

    def selected_iids(self) -> list[str]:
        """Return all currently selected iids (for multi-select mode)."""
        return [str(s) for s in self.tree.selection()]

    def selected_values(self) -> tuple | None:
        iid = self.selected_iid()
        if iid is None:
            return None
        return self.tree.item(iid, "values")

    def _handle_select(self, _event=None) -> None:
        if self._on_select:
            self._on_select(self.selected_iid())

    def _scroll_vertical(self, delta: int) -> str:
        if self._virtual_active:
            self._virtual_scroll_by_units(-delta, "units")
        else:
            self.tree.yview_scroll(delta, "units")
        return "break"

    # Excel-like helpers
    def _on_mousewheel(self, event) -> None:
        import sys

        if sys.platform == "darwin":
            delta = -event.delta
        else:
            delta = int(-event.delta / 120) if event.delta else 0
        if delta:
            self._scroll_vertical(delta)
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
        if self._sort_col == col:
            reverse = not self._sort_reverse
        self._sort_col = col
        self._sort_reverse = reverse
        try:
            col_index = self._column_ids.index(col)
        except ValueError:
            return

        def _key(values: tuple) -> tuple:
            val = values[col_index] if col_index < len(values) else ""
            try:
                cleaned = val.replace(",", "").replace("—", "").strip()
                if cleaned and cleaned.replace(".", "", 1).replace("-", "", 1).isdigit():
                    return (0, float(cleaned))
            except (ValueError, TypeError):
                pass
            return (1, val.lower())

        if self._virtual_active:
            order = sorted(range(len(self._virtual_rows)), key=lambda i: _key(self._virtual_rows[i]), reverse=reverse)
            self._virtual_rows = [self._virtual_rows[index] for index in order]
            self._virtual_iids = [self._virtual_iids[index] for index in order]
            if self._virtual_tags is not None:
                self._virtual_tags = [self._virtual_tags[index] for index in order]
            self._virtual_offset = 0
            self._render_virtual_window()
            return

        rows: list[tuple[tuple, str]] = []
        for iid in self.tree.get_children(""):
            vals = self.tree.item(iid, "values")
            rows.append((vals, str(iid)))
        rows.sort(key=lambda pair: _key(pair[0]), reverse=reverse)
        for index, (_vals, iid) in enumerate(rows):
            self.tree.move(iid, "", index)
