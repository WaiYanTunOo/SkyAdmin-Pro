from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry


class TaxIdsTabMixinMixin3:
    def _TaxIdsTabMixin_build_tax_ids_p2(self, cred_card):
        cred_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 8))
        cred_card.grid_columnconfigure(0, weight=1)
        self._client_cred_rows: dict[str, dict] = {}
        self._selected_client_cred_id: int | None = None

        ctk.CTkLabel(
            cred_card,
            text="Client portal logins (read-only)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))
        ctk.CTkLabel(
            cred_card,
            text="DBD, RD, IRD, and other types — edit in Office Hub → Passwords → Client DBD / RD.",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        self.client_cred_tree = ThemedTreeview(
            cred_card,
            columns=(
                ("type", "Type", 90),
                ("login", "Login ID", 140),
                ("portal", "Portal URL", 200),
            ),
            on_select=self._on_client_cred_select,
            showheight=4,
            table_id="company.tax_ids",
            db=self.app.db,
        )
        self.client_cred_tree.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))

        cred_detail = ctk.CTkFrame(cred_card, fg_color="transparent")
        cred_detail.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        cred_detail.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cred_detail, text="Password", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cred_pw_entry = themed_entry(cred_detail, textvariable=self.cred_pw_var, show="*", state="disabled")
        self.cred_pw_entry.grid(row=0, column=1, sticky="ew")
        ctk.CTkButton(cred_detail, text="Copy", width=70, command=self._copy_client_cred_password).grid(
            row=0, column=2, padx=(8, 0)
        )

        cred_actions = ctk.CTkFrame(cred_card, fg_color="transparent")
        cred_actions.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkButton(
            cred_actions,
            text="Edit in Office Hub",
            width=140,
            command=self._open_office_hub_credentials,
        ).pack(side="left")

    def _TaxIdsTabMixin_build_tax_ids_p3(self, frame):
        ctk.CTkButton(
            frame,
            text="Save Tax IDs & Service Info",
            width=200,
            command=self._save_tax_ids,
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(8, 14))

        self.acct_txn_volume.configure(command=self._on_txn_volume_change)
