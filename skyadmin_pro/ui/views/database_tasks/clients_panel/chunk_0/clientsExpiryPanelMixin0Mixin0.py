from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_entry


class ClientsExpiryPanelMixin0Mixin0:
    def __init__(self, master, app, feedback: FeedbackLabel, *, mode: str = "both") -> None:
        super().__init__(master, fg_color="transparent")
        self._panel_mode = mode if mode in ("clients", "expiry", "both") else "both"
        left, title_row = self._ClientsExpiryPanelMixin0__init__p1(app, feedback)
        client_pager = self._ClientsExpiryPanelMixin0__init__p2(title_row, left)
        actions = self._ClientsExpiryPanelMixin0__init__p3(client_pager, left)
        batch_row = self._ClientsExpiryPanelMixin0__init__p4(actions, left)
        form, right = self._ClientsExpiryPanelMixin0__init__p5(batch_row)
        self._ClientsExpiryPanelMixin0__init__p6(form, right)
        self._apply_panel_mode(left, right)

    def _apply_panel_mode(self, left, right) -> None:
        """Show only the Clients list, only Expiry, or both (legacy split)."""
        mode = getattr(self, "_panel_mode", "both")
        if mode == "clients":
            right.grid_remove()
            self.grid_columnconfigure(1, weight=0, minsize=0)
            left.grid(row=0, column=0, sticky="nsew", padx=0)
        elif mode == "expiry":
            left.grid_remove()
            self.grid_columnconfigure(1, weight=0, minsize=0)
            right.grid(row=0, column=0, sticky="nsew")
        # mode == "both": leave the default left/right grid from init.

    def _ClientsExpiryPanelMixin0__init__p1(self, app, feedback):
        self.app = app
        self.feedback = feedback
        self._refresh_seq = 0
        self._table_seq = 0
        self._page = 0
        self._page_size = 250
        self._has_more = False
        from skyadmin_pro.services.undo_manager import UndoManager

        self._undo = UndoManager()
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=400)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)
        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        title_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(title_row, text="Company List", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.search_var = ctk.StringVar()
        self._search_after: str | None = None
        self.search_var.trace_add("write", lambda *_args: self._debounced_search())
        search_box = ctk.CTkFrame(title_row, fg_color="transparent")
        search_box.grid(row=0, column=1, sticky="ew", padx=(12, 8))
        search_box.grid_columnconfigure(0, weight=1)
        self.search_entry = themed_entry(
            search_box,
            textvariable=self.search_var,
            placeholder_text="Search name / email",
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
        self._group_filter_var = ctk.StringVar(value="All")
        return left, title_row
