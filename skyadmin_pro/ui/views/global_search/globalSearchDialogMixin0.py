from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CONTENT_PAD
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_entry


class GlobalSearchDialogMixin0:
    """Modal search dialog that queries across all data types."""

    def __init__(self, app: object) -> None:
        super().__init__(app)
        self.app = app
        self.title("Global Search")
        self.geometry("700x520")
        self.resizable(True, True)
        self.transient(app)
        # Non-blocking modal grab — wait_visibility() inside after() is a nested
        # event loop that hangs if the window is closed before it fires.
        self.bind("<Map>", lambda _e: self.grab_set(), add="+")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Search input ──────────────────────────────────────────────
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.grid(row=0, column=0, sticky="ew", padx=CONTENT_PAD, pady=(CONTENT_PAD, 8))
        input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(input_frame, text="Search:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, padx=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._schedule_search())
        search_entry = themed_entry(
            input_frame,
            textvariable=self.search_var,
            placeholder_text="Type to search clients, tasks, documents, contacts…",
        )
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.focus_set()
        search_entry.bind("<Return>", lambda _: self._run_search())
        self.bind("<Escape>", lambda _: self.destroy())

        # ── Filter tabs ───────────────────────────────────────────────
        self._filter = ctk.StringVar(value="all")
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, 8))

        for label, value in [
            ("All", "all"),
            ("Clients", "clients"),
            ("Tasks", "tasks"),
            ("Docs", "docs"),
            ("Contacts", "contacts"),
        ]:
            ctk.CTkRadioButton(
                filter_frame,
                text=label,
                variable=self._filter,
                value=value,
                command=self._run_search,
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 12))

        # ── Results ───────────────────────────────────────────────────
        self._results_frame = ctk.CTkScrollableFrame(self, corner_radius=8)
        self._results_frame.grid(row=2, column=0, sticky="nsew", padx=CONTENT_PAD, pady=(0, 8))
        self._results_frame.grid_columnconfigure(0, weight=1)

        self.feedback = FeedbackLabel(self)
        self.feedback.grid(row=3, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, CONTENT_PAD))

        self._search_after = None
        self._last_query = ""
        self._search_seq = 0

    def destroy(self) -> None:
        try:
            if self._search_after is not None:
                self.after_cancel(self._search_after)
        except Exception as e:
            import logging

            logging.error(f"UI Error: {e}")
        self._search_after = None
        super().destroy()

    def _schedule_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")
            self._search_after = None
        try:
            self._search_after = self.after(250, self._run_search)
        except Exception:
            self._search_after = None
