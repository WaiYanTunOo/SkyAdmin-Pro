"""Sync conflict review dialog (Settings → License)."""

from __future__ import annotations

from collections.abc import Callable
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import make_modal


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

    tree = ThemedTreeview(
        top,
        columns=(
            ("logged", "Logged", 130),
            ("table", "Table", 110),
            ("global_id", "Global ID", 200),
            ("direction", "Dir", 50),
            ("local", "Local updated", 120),
            ("remote", "Remote updated", 120),
        ),
        showheight=16,
        on_double_click=_copy_gid,
    )
    tree.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))

    def _selected_table() -> str | None:
        choice = (filter_var.get() or "").strip()
        if not choice or choice == "All tables":
            return None
        return choice

    def _reload() -> None:
        tname = _selected_table()
        rows = db.list_sync_conflicts(limit=500, table_name=tname)
        shown = len(rows)
        if tname:
            summary = f"Showing {shown} conflict(s) in {tname} (of {total} total) — local data was kept."
        else:
            summary = (
                f"{total} conflict(s) logged — your local data was kept."
                if shown >= total
                else f"Showing {shown} of {total} conflict(s) — your local data was kept."
            )
        summary_lbl.configure(
            text=(f"{summary} Double-click a row to copy its Global ID. Clear log removes the audit only.")
        )
        tree.set_rows(
            [
                (
                    str(row.get("logged_at") or "")[:19],
                    row.get("table_name") or "",
                    row.get("global_id") or "",
                    row.get("direction") or "",
                    str(row.get("local_updated_at") or "")[:19],
                    str(row.get("remote_updated_at") or "")[:19],
                )
                for row in rows
            ]
        )

    table_menu.configure(command=lambda _choice: _reload())

    actions = ctk.CTkFrame(top, fg_color="transparent")
    actions.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
    actions.grid_columnconfigure(0, weight=1)

    def _clear() -> None:
        current_total = db.count_sync_conflicts()
        if not messagebox.askyesno(
            "Clear conflict log",
            f"Remove all {current_total} logged conflict(s)?\n\n"
            "This only clears the audit log — your data is unchanged.",
            parent=top,
        ):
            return
        cleared = db.clear_sync_conflicts()
        feedback.success(f"Cleared {cleared} sync conflict log entries.")
        if on_cleared:
            on_cleared()
        top.destroy()

    ctk.CTkButton(
        actions,
        text="Clear log",
        width=100,
        fg_color=("#b45309", "#92400e"),
        command=_clear,
    ).pack(side="left")
    ctk.CTkButton(actions, text="Refresh", width=90, command=_reload).pack(side="left", padx=(8, 0))
    ctk.CTkButton(actions, text="Copy Global ID", width=120, command=_copy_gid).pack(side="left", padx=(8, 0))
    ctk.CTkButton(actions, text="Close", width=90, command=top.destroy).pack(side="right")

    _reload()
