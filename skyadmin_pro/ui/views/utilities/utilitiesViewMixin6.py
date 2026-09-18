from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import make_modal, themed_scrollable_frame


class UtilitiesViewMixin6:
    def _show_history(self) -> None:
        versions = self.app.db.list_snippet_versions()
        if not versions:
            self.hub_feedback.info("No message versions saved yet — edit messages first.")
            return
        top = ctk.CTkToplevel(self)
        top.title("Message history")
        top.geometry("620x520")
        top.transient(self.winfo_toplevel())
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)

        scroll = themed_scrollable_frame(top, corner_radius=12)
        scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 8))
        scroll.grid_columnconfigure(0, weight=1)

        def rebuild() -> None:
            for child in scroll.winfo_children():
                child.destroy()
            for version in self.app.db.list_snippet_versions():
                row = ctk.CTkFrame(scroll, corner_radius=8)
                row.grid(row=len(scroll.winfo_children()), column=0, sticky="ew", padx=6, pady=4)
                row.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(
                    row,
                    text=version["created_at"],
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w",
                ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
                note = version["note"] or f"{version['count']} customized message(s)"
                ctk.CTkLabel(
                    row,
                    text=note,
                    text_color=TEXT_MUTED,
                    anchor="w",
                ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
                ctk.CTkButton(
                    row,
                    text="Restore",
                    width=90,
                    command=lambda vid=version["id"]: self._restore_version(vid, top, rebuild),
                ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(6, 6), pady=8)
                ctk.CTkButton(
                    row,
                    text="Export",
                    width=80,
                    fg_color="transparent",
                    border_width=1,
                    command=lambda vid=version["id"]: self._export_version(vid),
                ).grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, 12), pady=8)

        rebuild()

    def _restore_version(self, version_id: int, top, rebuild) -> None:
        if not messagebox.askyesno(
            "Restore messages",
            "Restore these messages as the active versions?\nA 'restored' entry is kept in history.",
            parent=top,
        ):
            return
        self.app.db.restore_snippet_version(version_id)
        self._load_snippets()
        self._build_hub()
        rebuild()
        self.hub_feedback.success(f"Version {version_id} restored.")
        self.app.set_status(f"Restored messages version {version_id}.")

    def _section_header(self, master, row: int, section: str, text: str) -> None:
        frame = ctk.CTkFrame(master, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=(14, 4))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text=text,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            frame,
            text="Customize",
            width=110,
            height=26,
            fg_color="transparent",
            border_width=1,
            command=lambda s=section: self._edit_snippets(section=s),
        ).grid(row=0, column=1, sticky="e")
