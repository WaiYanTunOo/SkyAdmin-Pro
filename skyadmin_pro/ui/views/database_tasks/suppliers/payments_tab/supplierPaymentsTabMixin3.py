from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE
from skyadmin_pro.ui.widgets import DatePickerField, themed_entry


class SupplierPaymentsTabMixin3:
    def _SupplierPaymentsTab__init__p1(self, host, master):
        self.host = host
        self.app = host.app
        self.feedback = host.feedback
        self._editing_payment_id: int | None = None

        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)
        pay_card = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        pay_card.grid(row=0, column=0, sticky="nsew")
        pay_card.grid_columnconfigure(0, weight=1)
        pay_card.grid_rowconfigure(3, weight=1)
        # Column hide/show: ThemedTreeview built-in ⋮ Columns only (no duplicate button).
        ctk.CTkLabel(
            pay_card,
            text="Supplier payments (AP)",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        pay_form = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_form.grid(row=1, column=0, sticky="ew", padx=16)
        pay_form.grid_columnconfigure(1, weight=1)
        pay_form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(pay_form, text="Supplier").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pay_supplier = ctk.CTkComboBox(pay_form, values=[""])
        self.pay_supplier.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Client").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.pay_client = ctk.CTkComboBox(pay_form, values=[""])
        self.pay_client.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Amount (THB)").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pay_amount = themed_entry(pay_form, placeholder_text="e.g. 15000")
        self.pay_amount.bind("<FocusOut>", lambda _e: self._format_pay_amount())
        self.pay_amount.grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Due date").grid(row=1, column=2, sticky="w", padx=(12, 8), pady=4)
        self.pay_due_var = ctk.StringVar()
        DatePickerField(pay_form, var=self.pay_due_var).grid(row=1, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Payment date").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pay_date_var = ctk.StringVar()
        DatePickerField(pay_form, var=self.pay_date_var).grid(row=2, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Notes").grid(row=2, column=2, sticky="w", padx=(12, 8), pady=4)
        self.pay_notes = themed_entry(pay_form)
        self.pay_notes.grid(row=2, column=3, sticky="ew", pady=4)
        return pay_card
