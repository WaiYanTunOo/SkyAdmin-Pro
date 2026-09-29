from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CONTENT_PAD
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_entry


class GlobalSearchDialogMixin0:
    """Magic Search — find records across the local database."""

    def __init__(self, app: object) -> None:
        super().__init__(app)
        self.app = app
        self.title("Magic Search")
        self.geometry("740x560")
        self.resizable(True, True)
        self.transient(app)
        self.bind("<Map>", lambda _e: self.grab_set(), add="+")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.grid(row=0, column=0, sticky="ew", padx=CONTENT_PAD, pady=(CONTENT_PAD, 8))
        input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(input_frame, text="Find:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, padx=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._schedule_search())
        search_entry = themed_entry(
            input_frame,
            textvariable=self.search_var,
            placeholder_text="Company, under 30 days, service, document…",
        )
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.focus_set()
        search_entry.bind("<Return>", lambda _: self._on_return())
        self.bind("<Escape>", lambda _: self.destroy())

        self._filter = ctk.StringVar(value="all")
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, 8))
        filters = [
            ("All", "all"),
            ("Clients", "clients"),
            ("Pipeline", "pipeline"),
            ("Expiry", "expiry"),
            ("Docs", "docs"),
            ("Contacts", "contacts"),
            ("Suppliers", "suppliers"),
            ("Courier", "courier"),
        ]
        for i, (label, value) in enumerate(filters):
            ctk.CTkRadioButton(
                filter_frame,
                text=label,
                variable=self._filter,
                value=value,
                command=self._run_search,
                font=ctk.CTkFont(size=11),
            ).grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 10), pady=2)

        self._results_frame = ctk.CTkScrollableFrame(self, corner_radius=8)
        self._results_frame.grid(row=2, column=0, sticky="nsew", padx=CONTENT_PAD, pady=(0, 8))
        self._results_frame.grid_columnconfigure(0, weight=1)
        self.feedback = FeedbackLabel(self)
        self.feedback.grid(row=3, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, CONTENT_PAD))
        self._search_after = None
        self._last_query = ""
        self._search_seq = 0
        self._hits: list[dict] = []

    def destroy(self) -> None:
        try:
            if self._search_after is not None:
                self.after_cancel(self._search_after)
        except Exception:
            pass
        self._search_after = None
        super().destroy()

    def _schedule_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception:
                pass
            self._search_after = None
        try:
            self._search_after = self.after(250, self._run_search)
        except Exception:
            self._search_after = None
