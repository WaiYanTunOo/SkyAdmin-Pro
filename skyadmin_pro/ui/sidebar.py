"""SidebarWidget — grouped nav buttons that replace the flat 11-item list."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

from skyadmin_pro.config import NAV_GROUPS
from skyadmin_pro.services.i18n import tr
from skyadmin_pro.ui.sidebar_groups import (
    group_for_child,
    load_group_states,
    save_group_state,
)
from skyadmin_pro.ui.sidebar_tooltip import SidebarTooltip
from skyadmin_pro.ui.theme import (
    SIDEBAR_ACTIVE_BG,
    SIDEBAR_ACTIVE_TEXT,
    SIDEBAR_BUTTON_HEIGHT,
    SIDEBAR_HOVER_BG,
    SIDEBAR_ICONS,
    SIDEBAR_PADX,
    SIDEBAR_PADY,
    SIDEBAR_TEXT,
)

if TYPE_CHECKING:
    from skyadmin_pro.database import Database


class SidebarWidget:
    """Renders a grouped, collapsible sidebar inside *parent* (a CTkScrollableFrame)."""

    def __init__(
        self,
        parent: ctk.CTkScrollableFrame,
        db: Database,
        show_view: Callable[[str], None],
        *,
        collapsed: bool = False,
    ) -> None:
        self._parent = parent
        self._db = db
        self._show_view = show_view
        self._collapsed = collapsed
        self._group_open: dict[str, bool] = load_group_states(db)
        # {key: button widget} — both group rows and child rows
        self._buttons: dict[str, ctk.CTkButton] = {}
        # {group_key: list of child (key, button) pairs}
        self._children: dict[str, list[tuple[str, ctk.CTkButton]]] = {}
        self._tooltips: dict[str, SidebarTooltip] = {}
        self._active_key: str | None = None
        self._build()

    # ── Public API ────────────────────────────────────────────────────────

    def highlight(self, key: str) -> None:
        self._active_key = key
        for k, btn in self._buttons.items():
            if k == key:
                btn.configure(fg_color=SIDEBAR_ACTIVE_BG, text_color=SIDEBAR_ACTIVE_TEXT, hover_color=SIDEBAR_ACTIVE_BG)
            else:
                btn.configure(fg_color="transparent", text_color=SIDEBAR_TEXT, hover_color=SIDEBAR_HOVER_BG)

    def ensure_group_expanded(self, child_key: str) -> None:
        group_key = group_for_child(child_key)
        if group_key and not self._group_open.get(group_key, False):
            self._set_group_open(group_key, True)

    def apply_layout(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        for key, btn in self._buttons.items():
            icon = SIDEBAR_ICONS.get(key, "•")
            is_group = key.startswith("group_")
            children = self._children.get(key, [])
            if collapsed:
                glyph = "" if not children else (" ▸" if not self._group_open.get(key) else " ▾")
                btn.configure(text=icon + glyph, anchor="center")
                btn.grid_configure(padx=8)
                if key not in self._tooltips:
                    tip_text = self._tooltip_text(key)
                    self._tooltips[key] = SidebarTooltip(btn, tip_text)
            else:
                label = self._label_for(key)
                if children:
                    glyph = " ▾" if self._group_open.get(key) else " ▸"
                    btn.configure(text=f"{icon}  {tr(label)}{glyph}", anchor="w")
                else:
                    btn.configure(text=f"{icon}  {tr(label)}", anchor="w")
                btn.grid_configure(padx=SIDEBAR_PADX if not is_group else SIDEBAR_PADX)
                tip = self._tooltips.pop(key, None)
                if tip:
                    tip._hide()
        self._refresh_child_visibility()

    # ── Internal ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        row = 0
        self._labels: dict[str, str] = {}
        for group_key, label, children in NAV_GROUPS:
            self._labels[group_key] = label
            btn = self._make_button(group_key, label, children, row)
            self._buttons[group_key] = btn
            row += 1
            if children:
                child_btns: list[tuple[str, ctk.CTkButton]] = []
                for child_key in children:
                    child_label = self._child_label(child_key)
                    self._labels[child_key] = child_label
                    cbtn = self._make_child_button(child_key, child_label, row)
                    self._buttons[child_key] = cbtn
                    child_btns.append((child_key, cbtn))
                    row += 1
                self._children[group_key] = child_btns
        self._refresh_child_visibility()

    def _make_button(self, key: str, label: str, children: tuple, row: int) -> ctk.CTkButton:
        icon = SIDEBAR_ICONS.get(key, "•")
        glyph = (" ▾" if self._group_open.get(key) else " ▸") if children else ""
        text = f"{icon}  {tr(label)}{glyph}" if not self._collapsed else icon + glyph
        cmd = (lambda k=key: self._on_group_click(k)) if children else (lambda k=key: self._show_view(k))
        btn = ctk.CTkButton(
            self._parent,
            text=text,
            height=SIDEBAR_BUTTON_HEIGHT,
            corner_radius=10,
            anchor="w" if not self._collapsed else "center",
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=SIDEBAR_TEXT,
            hover_color=SIDEBAR_HOVER_BG,
            command=cmd,
        )
        padx = 8 if self._collapsed else SIDEBAR_PADX
        btn.grid(row=row, column=0, sticky="ew", padx=padx, pady=SIDEBAR_PADY)
        return btn

    def _make_child_button(self, key: str, label: str, row: int) -> ctk.CTkButton:
        icon = SIDEBAR_ICONS.get(key, "•")
        text = f"{icon}  {tr(label)}" if not self._collapsed else icon
        btn = ctk.CTkButton(
            self._parent,
            text=text,
            height=SIDEBAR_BUTTON_HEIGHT - 4,
            corner_radius=8,
            anchor="w" if not self._collapsed else "center",
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            text_color=SIDEBAR_TEXT,
            hover_color=SIDEBAR_HOVER_BG,
            command=lambda k=key: self._show_view(k),
        )
        padx = 8 if self._collapsed else SIDEBAR_PADX + 18
        btn.grid(row=row, column=0, sticky="ew", padx=padx, pady=(2, 2))
        return btn

    def _on_group_click(self, group_key: str) -> None:
        is_open = self._group_open.get(group_key, False)
        children = self._children.get(group_key, [])
        if not is_open and children:
            # Open group and navigate to first child if none is active
            self._set_group_open(group_key, True)
            active_keys = {k for k, _ in children}
            if self._active_key not in active_keys:
                self._show_view(children[0][0])
        else:
            self._set_group_open(group_key, not is_open)

    def _set_group_open(self, group_key: str, open_: bool) -> None:
        self._group_open[group_key] = open_
        save_group_state(self._db, group_key, open_)
        self._refresh_group_button(group_key)
        self._refresh_child_visibility()

    def _refresh_group_button(self, group_key: str) -> None:
        btn = self._buttons.get(group_key)
        if btn is None:
            return
        icon = SIDEBAR_ICONS.get(group_key, "•")
        label = self._labels.get(group_key, group_key)
        open_ = self._group_open.get(group_key, False)
        glyph = " ▾" if open_ else " ▸"
        if self._collapsed:
            btn.configure(text=icon + glyph)
        else:
            btn.configure(text=f"{icon}  {tr(label)}{glyph}")

    def _refresh_child_visibility(self) -> None:
        for group_key, child_list in self._children.items():
            visible = self._group_open.get(group_key, False)
            for _key, cbtn in child_list:
                if visible:
                    cbtn.grid()
                else:
                    cbtn.grid_remove()

    def _label_for(self, key: str) -> str:
        return self._labels.get(key, key)

    def _child_label(self, key: str) -> str:
        """Resolve child label from NAV_ITEMS flat list."""
        from skyadmin_pro.config import NAV_ITEMS

        return dict(NAV_ITEMS).get(key, key)

    def _tooltip_text(self, key: str) -> str:
        label = self._labels.get(key, key)
        children = self._children.get(key, [])
        if children:
            child_labels = ", ".join(self._labels.get(k, k) for k, _ in children)
            return f"{label}: {child_labels}"
        return label
