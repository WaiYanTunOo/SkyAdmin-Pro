"""Shared rollout queue UI for Accounting, VO/CSH, and Office Hub setup tabs."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import bind_wrap_label

_SETUP_FILTERS = ("All", "Needs setup", "Ready")
_STATUS_TAGS = {
    "Ready": ("done",),
    "Almost": ("watch",),
    "Needs setup": ("urgent",),
}


@dataclass(frozen=True)
class RolloutAction:
    text: str
    command: Callable[[], None]
    width: int = 120
    fg_color: str | tuple[str, str] | None = None
    border_width: int = 0


class SetupRolloutPanel(ctk.CTkFrame):
    """Filterable rollout table with summary line and action buttons."""

    def __init__(
        self,
        master,
        *,
        title: str,
        description: str,
        columns: Sequence[tuple[str, str, int]],
        actions: Sequence[RolloutAction],
        on_select: Callable[[str | None], None] | None = None,
        on_double_click: Callable[[str | None], None] | None = None,
        showheight: int = 10,
        use_card: bool = True,
        tree_sticky: str = "ew",
        tree_row_weight: int = 0,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        container = self
        if use_card:
            container = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
            container.grid(row=0, column=0, sticky="nsew")
            container.grid_columnconfigure(0, weight=1)
            if tree_row_weight:
                container.grid_rowconfigure(3, weight=tree_row_weight)
        self.grid_columnconfigure(0, weight=1)
        if tree_row_weight:
            self.grid_rowconfigure(0, weight=1)
        if tree_row_weight and not use_card:
            self.grid_rowconfigure(3, weight=tree_row_weight)

        self._container = container
        self._rows: dict[str, dict[str, Any]] = {}
        self._selected_id: int | None = None
        self._row_cells_fn: Callable[[dict[str, Any]], tuple[Any, ...]] | None = None

        ctk.CTkLabel(
            container,
            text=title,
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        desc_label = ctk.CTkLabel(
            container,
            text=description,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        desc_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        bind_wrap_label(desc_label, container, pad=40)

        toolbar = ctk.CTkFrame(container, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        ctk.CTkLabel(toolbar, text="Show", anchor="w").grid(row=0, column=0, padx=(0, 8))
        self.filter_menu = ctk.CTkOptionMenu(
            toolbar,
            values=list(_SETUP_FILTERS),
            command=lambda _c: self.refresh(),
            width=140,
        )
        self.filter_menu.set("All")
        self.filter_menu.grid(row=0, column=1, sticky="w")
        self.summary_label = ctk.CTkLabel(toolbar, text="", text_color=TEXT_MUTED, anchor="w")
        self.summary_label.grid(row=0, column=2, sticky="ew", padx=(16, 0))
        toolbar.grid_columnconfigure(2, weight=1)

        self.tree = ThemedTreeview(
            container,
            columns=tuple(columns),
            on_select=self._on_tree_select,
            on_double_click=on_double_click,
            showheight=showheight,
        )
        sticky = tree_sticky
        if tree_row_weight:
            sticky = f"{tree_sticky}n" if "n" not in tree_sticky else tree_sticky
        self.tree.grid(row=3, column=0, sticky=sticky, padx=16, pady=(0, 8))

        action_row = ctk.CTkFrame(container, fg_color="transparent")
        action_row.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 14))
        for idx, action in enumerate(actions):
            kwargs: dict[str, Any] = {"width": action.width, "command": action.command}
            if action.fg_color is not None:
                kwargs["fg_color"] = action.fg_color
            if action.border_width:
                kwargs["border_width"] = action.border_width
            ctk.CTkButton(action_row, text=action.text, **kwargs).grid(
                row=0, column=idx, padx=(0, 8) if idx < len(actions) - 1 else 0
            )

        self._list_rows_fn: Callable[[], list[dict[str, Any]]] | None = None
        self._summary_fn: Callable[[int, int], str] | None = None
        self._external_on_select = on_select

    def configure_data(
        self,
        *,
        list_rows: Callable[[], list[dict[str, Any]]],
        row_cells: Callable[[dict[str, Any]], tuple[Any, ...]],
        summary: Callable[[int, int], str],
    ) -> None:
        self._list_rows_fn = list_rows
        self._row_cells_fn = row_cells
        self._summary_fn = summary

    def refresh(self) -> None:
        if self._list_rows_fn is None or self._row_cells_fn is None or self._summary_fn is None:
            return
        self.tree.apply_theme()
        rows = self._list_rows_fn()
        ready = sum(1 for row in rows if not row.get("setup_missing"))
        self.summary_label.configure(text=self._summary_fn(ready, len(rows)))

        filt = self.filter_menu.get()
        if filt == "Needs setup":
            rows = [row for row in rows if row.get("setup_missing")]
        elif filt == "Ready":
            rows = [row for row in rows if not row.get("setup_missing")]

        self._rows = {}
        tree_rows: list[tuple[Any, ...]] = []
        iids: list[str] = []
        tags: list[tuple[str, ...]] = []
        for row in rows:
            iid = str(row["id"])
            self._rows[iid] = row
            iids.append(iid)
            tree_rows.append(self._row_cells_fn(row))
            status = row.get("setup_status")
            tags.append(_STATUS_TAGS.get(status, ("urgent",)))
        self.tree.set_rows(tree_rows, iids=iids, tags=tags, empty_message="No clients in this rollout queue.")

    def selected_row(self) -> dict[str, Any] | None:
        if self._selected_id is None:
            return None
        return self._rows.get(str(self._selected_id))

    def _on_tree_select(self, iid: str | None) -> None:
        self._selected_id = int(iid) if iid else None
        if self._external_on_select is not None:
            self._external_on_select(iid)
