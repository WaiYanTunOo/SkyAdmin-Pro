from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.treeview import ThemedTreeview


class SupplierPaymentsTabMixin4:
    def _SupplierPaymentsTab__init__p2(self, pay_card):
        pay_form_btns = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_form_btns.grid(row=2, column=0, sticky="w", padx=16, pady=(8, 4))
        self.pay_save_btn = ctk.CTkButton(pay_form_btns, text="Add payment", width=120, command=self._save_payment)
        self.pay_save_btn.pack(side="left")
        ctk.CTkButton(pay_form_btns, text="Edit", width=70, command=self._edit_payment).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            pay_form_btns,
            text="New",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._new_payment,
        ).pack(side="left", padx=(8, 0))

        self.pay_tree = ThemedTreeview(
            pay_card,
            columns=(
                ("supplier", "Supplier", 150),
                ("client", "Client", 130),
                ("amount", "Amount", 90),
                ("due", "Due date", 90),
                ("paid", "Paid", 60),
                ("paid_date", "Paid date", 90),
                ("notes", "Notes", 160),
            ),
            showheight=10,
            table_id="suppliers.payments",
            db=self.app.db,
        )
        self.pay_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        pay_btns = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_btns.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkButton(pay_btns, text="Mark paid", width=110, command=self._mark_paid).pack(side="left")
        ctk.CTkButton(
            pay_btns,
            text="Delete",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self._delete_payment,
        ).pack(side="left", padx=(8, 0))
