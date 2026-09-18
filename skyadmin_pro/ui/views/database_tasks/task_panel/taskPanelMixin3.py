from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.ui.theme import FORM_SIDEBAR_MIN_WIDTH, TEXT_MUTED
from skyadmin_pro.ui.widgets import themed_entry


class TaskPanelMixin3:
    def _delete(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select a task first.")
            return
        if not messagebox.askyesno(
            "Delete task",
            "Delete this task? Courier logs linked to it will be kept.",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            self.app.db.delete_task(self._editing_id)
        except Exception as exc:
            self.feedback.error(f"Could not delete task: {exc}")
            return
        self.feedback.success("Task deleted.")
        self._new()
        self.refresh()
        self.app.invalidate_dashboard()

    def _TaskPanel__init__p1(self, app, feedback):
        self.app = app
        self.feedback = feedback
        self._editing_id: int | None = None
        self._refresh_seq = 0
        self._page = 0
        self._page_size = 250
        self._has_more = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=FORM_SIDEBAR_MIN_WIDTH)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.filter = ctk.CTkSegmentedButton(
            top,
            values=["Pending", "Completed", "All"],
            command=lambda _v: (setattr(self, "_page", 0), self.refresh()),
        )
        self.filter.set("Pending")
        self.filter.pack(side="left")

        self.search_var = ctk.StringVar()
        self._search_after: str | None = None
        self.search_var.trace_add("write", lambda *_args: self._debounced_search())
        search_box = ctk.CTkFrame(top, fg_color="transparent")
        search_box.pack(side="left", fill="x", expand=True, padx=(12, 12))
        search_box.grid_columnconfigure(0, weight=1)
        self.search_entry = themed_entry(
            search_box,
            textvariable=self.search_var,
            placeholder_text="Search task / client / category…",
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda _e: self._run_search())
        self.clear_search_btn = ctk.CTkButton(
            search_box,
            text="✕",
            width=26,
            height=26,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=TEXT_MUTED,
            command=self._clear_search,
        )
        self.clear_search_btn.grid(row=0, column=1, padx=(4, 0))
        return top
