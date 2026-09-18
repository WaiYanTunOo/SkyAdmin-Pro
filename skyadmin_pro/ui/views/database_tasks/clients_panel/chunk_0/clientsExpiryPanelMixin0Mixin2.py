from __future__ import annotations

import customtkinter as ctk


class ClientsExpiryPanelMixin0Mixin2:
    def _ClientsExpiryPanelMixin0__init__p3(self, client_pager, left):
        self.client_next = ctk.CTkButton(
            client_pager,
            text="Next ▶",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._client_next_page,
        )
        self.client_next.pack(side="left")
        self.client_page_size = ctk.CTkOptionMenu(
            client_pager,
            values=["100", "250", "500", "1000"],
            width=90,
            command=self._on_client_page_size,
        )
        self.client_page_size.set("250")
        self.client_page_size.pack(side="right")
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 4))
        ctk.CTkButton(actions, text="Add / Edit client", width=125, command=self._open_client_dialog).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Groups…",
            width=85,
            fg_color="transparent",
            border_width=1,
            command=self._manage_groups,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="View company details",
            width=155,
            fg_color="transparent",
            border_width=1,
            command=self._view_company_details,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Generate Workspace",
            width=150,
            command=self._generate_workspace,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Open client folder",
            width=135,
            fg_color="transparent",
            border_width=1,
            command=self._open_client_folder,
        ).pack(side="left", padx=(8, 0))
        return actions
