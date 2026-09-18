from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.treeview import ThemedTreeview


class SupplierServicesTabMixin2:
    def _SupplierServicesTab__init__p2(self, svc_btns, svc_card):
        ctk.CTkButton(
            svc_btns,
            text="Edit",
            width=70,
            command=self._edit_supplier_service,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            svc_btns,
            text="Delete",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._delete_supplier_service,
        ).pack(side="left", padx=(8, 0))

        self.supplier_svc_tree = ThemedTreeview(
            svc_card,
            columns=(
                ("company", "Company", 200),
                ("service", "Service", 200),
                ("expiry", "Expiry date", 120),
                ("notes", "Notes", 200),
            ),
            showheight=10,
            table_id="suppliers.services",
            db=self.app.db,
        )
        self.supplier_svc_tree.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))
