from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview


class TaxIdsTabMixinMixin3:
    def _TaxIdsTabMixin_build_tax_ids_p2(self, tree_card, frame):
        # Rows: 0 title, 1 form, 2 save, 3 tree, 4–5 labels, 6 cred FormField form.
        tree_card.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        tree_card.grid_columnconfigure(0, weight=1)
        self._client_cred_rows: dict[str, dict] = {}
        self._selected_client_cred_id: int | None = None
        self._cred_pw_visible = False

        ctk.CTkLabel(
            tree_card,
            text="Client portal logins",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))
        self.client_cred_tree = ThemedTreeview(
            tree_card,
            columns=(
                ("type", "Type", 90),
                ("login", "Login ID", 140),
                ("portal", "Portal URL", 200),
            ),
            on_select=self._on_client_cred_select,
            showheight=8,
            table_id="company.tax_ids",
            db=self.app.db,
        )
        self.client_cred_tree.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        ctk.CTkLabel(
            frame,
            text="Portal login details (encrypted)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=4, column=0, sticky="w", padx=16, pady=(8, 2))
        ctk.CTkLabel(
            frame,
            text="DBD, RD, IRD, and other portal logins — edit below; scroll the tab to move between form and tree.",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        ).grid(row=5, column=0, sticky="w", padx=16, pady=(0, 6))
        self._TaxIdsTabMixin_build_cred_form(frame)

    def _TaxIdsTabMixin_build_tax_ids_p3(self, frame):
        ctk.CTkButton(
            frame,
            text="Save Tax IDs & Service Info",
            width=200,
            command=self._save_tax_ids,
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(8, 8))
        self.acct_txn_volume.configure(command=self._on_txn_volume_change)
