from __future__ import annotations

from collections.abc import Callable
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import make_modal

from .build_conflict_tree import build_conflict_tree


def open_sync_conflicts_dialog(
    parent: ctk.CTkBaseClass,
    *,
    db: Any,
    feedback: Any,
    on_cleared: Callable[[], None] | None = None,
) -> None:
    """Show LWW conflict audit rows, or an empty-state info box."""
    total = db.count_sync_conflicts()
    if total <= 0:
        messagebox.showinfo(
            "Sync conflicts",
            "No sync conflicts logged.\n\n"
            "Conflicts are recorded when the server has older data than your PC "
            "(last-write-wins keeps your local copy).",
            parent=parent.winfo_toplevel(),
        )
        return

    top = ctk.CTkToplevel(parent)
    top.title("SkyAdmin Pro — Sync conflicts")
    top.geometry("920x560")
    top.minsize(720, 420)
    make_modal(top)
    top.grid_columnconfigure(0, weight=1)
    top.grid_rowconfigure(2, weight=1)

    tables = ["All tables"] + db.list_sync_conflict_tables()
    filter_var = ctk.StringVar(value="All tables")

    header = ctk.CTkFrame(top, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
    header.grid_columnconfigure(0, weight=1)

    summary_lbl = ctk.CTkLabel(
        header,
        text="",
        anchor="w",
        justify="left",
        text_color=TEXT_MUTED,
        wraplength=700,
    )
    summary_lbl.grid(row=0, column=0, sticky="ew")

    filter_row = ctk.CTkFrame(top, fg_color="transparent")
    filter_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
    ctk.CTkLabel(filter_row, text="Table:", text_color=TEXT_MUTED).pack(side="left", padx=(0, 8))
    table_menu = ctk.CTkOptionMenu(filter_row, values=tables, variable=filter_var, width=180)
    table_menu.pack(side="left")

    def _copy_gid(_iid: str | None = None) -> None:
        sel = tree.tree.selection()
        if not sel:
            return
        vals = tree.tree.item(sel[0], "values")
        if not vals or len(vals) < 3:
            return
        gid = str(vals[2] or "").strip()
        if not gid:
            return
        try:
            top.clipboard_clear()
            top.clipboard_append(gid)
            short = gid if len(gid) <= 18 else f"{gid[:18]}…"
            feedback.info(f"Copied Global ID: {short}")
        except Exception:
            feedback.error("Could not copy Global ID.")

    build_conflict_tree(top, db, feedback, filter_var, table_menu, total, summary_lbl, on_cleared, _copy_gid, None)
