from __future__ import annotations

import customtkinter as ctk


class ClientsExpiryPanelMixin5Mixin1:
    def _ClientsExpiryPanelMixin5_manage_groups_p1(
        self, body, add_group, rename_group, delete_group, top, refresh_menu
    ):
        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        ctk.CTkButton(btns, text="Add", width=80, command=add_group).pack(side="left")
        ctk.CTkButton(
            btns,
            text="Rename",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=rename_group,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            btns,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=delete_group,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(btns, text="Close", width=80, command=top.destroy).pack(side="right")

        refresh_menu()
