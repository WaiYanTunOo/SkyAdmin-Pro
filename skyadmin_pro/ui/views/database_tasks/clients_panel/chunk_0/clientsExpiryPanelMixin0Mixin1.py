from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview


class ClientsExpiryPanelMixin0Mixin1:
    def _ClientsExpiryPanelMixin0__init__p2(self, title_row, left):
        self.group_filter_menu = ctk.CTkOptionMenu(
            title_row,
            variable=self._group_filter_var,
            values=["All"],
            width=120,
            command=lambda _: self._refresh_clients(),
        )
        self.group_filter_menu.grid(row=0, column=2, padx=(0, 4))
        ctk.CTkLabel(
            title_row,
            text="(this PC only)",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=3, padx=(0, 8), sticky="w")
        ctk.CTkButton(
            title_row,
            text="Export to Excel",
            width=130,
            command=self._export_excel,
        ).grid(row=0, column=4, sticky="e", padx=(8, 0))
        self.client_tree = ThemedTreeview(
            left,
            columns=(
                ("company", "Company name", 210),
                ("contact", "Contact", 150),
                ("email", "Email", 220),
                ("status", "Status", 90),
            ),
            showheight=10,
            table_id="clients",
            db=self.app.db,
            selectmode="extended",
        )
        self.client_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 4))
        self.client_tree.tree.bind("<<TreeviewSelect>>", self._on_client_tree_select, add="+")
        left.grid_rowconfigure(1, weight=1)
        client_pager = ctk.CTkFrame(left, fg_color="transparent")
        client_pager.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))
        self.client_prev = ctk.CTkButton(
            client_pager,
            text="◀ Prev",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._client_prev_page,
        )
        self.client_prev.pack(side="left")
        self.client_page_label = ctk.CTkLabel(client_pager, text="Page 1", text_color=TEXT_MUTED)
        self.client_page_label.pack(side="left", padx=10)
        return client_pager
