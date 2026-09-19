from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import FONT_SIZE_SM, TEXT_MUTED
from skyadmin_pro.ui.widgets import themed_entry


class FinancialDocsPanelMixin0:
    """Cross-client search and browse for financial documents."""

    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_toolbar()
        self._build_treeview()
        self.refresh()

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        bar.grid_columnconfigure(1, weight=3)
        bar.grid_columnconfigure(3, weight=1)
        bar.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(bar, text="Search", font=("Segoe UI", FONT_SIZE_SM), text_color=TEXT_MUTED).grid(
            row=0, column=0, padx=(0, 4)
        )
        self.search_var = ctk.StringVar()
        self._search_after: str | None = None
        self.search_entry = themed_entry(
            bar, textvariable=self.search_var, placeholder_text="Folder tools — not the company file"
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda _: self._do_search())
        self.search_var.trace_add("write", lambda *_: self._debounced_search())

        ctk.CTkLabel(bar, text="Category", font=("Segoe UI", FONT_SIZE_SM), text_color=TEXT_MUTED).grid(
            row=0, column=2, padx=(0, 4)
        )
        from skyadmin_pro.config import FINANCIAL_DOC_CATEGORIES

        self.cat_var = ctk.StringVar(value="All")
        self.cat_menu = ctk.CTkOptionMenu(
            bar,
            variable=self.cat_var,
            values=["All"] + list(FINANCIAL_DOC_CATEGORIES),
            width=140,
        )
        self.cat_menu.grid(row=0, column=3, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(bar, text="Client", font=("Segoe UI", FONT_SIZE_SM), text_color=TEXT_MUTED).grid(
            row=0, column=4, padx=(0, 4)
        )
        self.client_var = ctk.StringVar(value="All")
        self.client_menu = ctk.CTkOptionMenu(
            bar,
            variable=self.client_var,
            values=["All"],
            width=180,
        )
        self.client_menu.grid(row=0, column=5, sticky="ew", padx=(0, 8))

        ctk.CTkButton(bar, text="Search", width=70, command=self._do_search).grid(row=0, column=6, padx=(8, 4))
        ctk.CTkButton(
            bar, text="Clear", width=60, fg_color="transparent", border_width=1, command=self._clear_search
        ).grid(row=0, column=7, padx=(0, 4))
        ctk.CTkButton(bar, text="Open", width=60, command=self._open_selected).grid(row=0, column=8, padx=(0, 4))
        ctk.CTkButton(bar, text="Refresh", width=70, fg_color="transparent", border_width=1, command=self.refresh).grid(
            row=0, column=9
        )

    def _build_treeview(self) -> None:
        from skyadmin_pro.ui.treeview import ThemedTreeview

        self.tree = ThemedTreeview(
            self,
            columns=(
                ("client", "Client", 160),
                ("date", "Date", 90),
                ("category", "Category", 120),
                ("filename", "File Name", 200),
                ("amount", "Amount", 90),
                ("description", "Description", 200),
            ),
            showheight=12,
            on_double_click=self._on_tree_double,
            table_id="document_hub.financial",
            db=self.app.db,
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        summary_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 4))
        self.summary_label = ctk.CTkLabel(summary_frame, text="", font=("Segoe UI", 11), text_color=TEXT_MUTED)
        self.summary_label.pack(side="left")

    def _populate_client_menu(self) -> None:
        clients = self.app.db.list_clients()
        names = sorted(c.get("name", "") for c in clients if c.get("name"))
        self.client_menu.configure(values=["All"] + names)
        # Preserve the current selection; only reset when it no longer exists.
        if self.client_var.get() not in ("All",) + tuple(names):
            self.client_var.set("All")

    def _debounced_search(self) -> None:
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")
        self._search_after = self.after(300, self._do_search)
