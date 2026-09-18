from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk


def _open_sync_conflicts_dialog_p1(top, db, feedback, on_cleared, _reload, _copy_gid):
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
