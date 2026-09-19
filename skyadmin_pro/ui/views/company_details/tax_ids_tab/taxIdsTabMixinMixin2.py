from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import ACCOUNTING_PRICING_SERVICES, PAYMENT_STATUSES, TRANSACTION_RANGES
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE
from skyadmin_pro.ui.widgets import DatePickerField, themed_entry


class TaxIdsTabMixinMixin2:
    def _TaxIdsTabMixin_build_tax_ids_p1(self, master, tree_master=None):
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Tax Identity & Service Contract",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure((0, 1), weight=1)

        self.tax_id_var = ctk.StringVar()
        self.cred_pw_var = ctk.StringVar()
        self.vat_reg_date_var = ctk.StringVar()
        self.service_fee_var = ctk.StringVar()
        self.sla_var = ctk.StringVar()
        self.headcount_var = ctk.StringVar()

        ctk.CTkLabel(form, text="Tax ID").grid(row=0, column=0, columnspan=2, sticky="w", pady=(2, 2))
        themed_entry(form, textvariable=self.tax_id_var).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="VAT Registered").grid(row=2, column=0, sticky="w", pady=(6, 2))
        self.vat_registered_var = ctk.BooleanVar()
        ctk.CTkCheckBox(form, text="Yes", variable=self.vat_registered_var).grid(
            row=3, column=0, sticky="w", pady=(0, 4)
        )
        ctk.CTkLabel(form, text="VAT Registration Date").grid(row=2, column=1, sticky="w", pady=(6, 2))
        DatePickerField(form, var=self.vat_reg_date_var).grid(row=3, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="Service Type").grid(row=4, column=0, sticky="w", pady=(6, 2))
        self.acct_service_type = ctk.CTkOptionMenu(form, values=["", *ACCOUNTING_PRICING_SERVICES])
        self.acct_service_type.grid(row=5, column=0, sticky="ew", padx=(0, 12), pady=(0, 4))
        ctk.CTkLabel(form, text="Transaction Volume").grid(row=4, column=1, sticky="w", pady=(6, 2))
        self.acct_txn_volume = ctk.CTkOptionMenu(form, values=list(TRANSACTION_RANGES))
        self.acct_txn_volume.grid(row=5, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="Service Fee (THB)").grid(row=6, column=0, sticky="w", pady=(6, 2))
        themed_entry(form, textvariable=self.service_fee_var).grid(
            row=7, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="Payment Status").grid(row=6, column=1, sticky="w", pady=(6, 2))
        self.acct_payment_status = ctk.CTkOptionMenu(form, values=list(PAYMENT_STATUSES))
        self.acct_payment_status.grid(row=7, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="SLA (hours)").grid(row=8, column=0, sticky="w", pady=(6, 2))
        themed_entry(form, textvariable=self.sla_var).grid(row=9, column=0, sticky="ew", padx=(0, 12), pady=(0, 4))
        ctk.CTkLabel(form, text="Headcount").grid(row=8, column=1, sticky="w", pady=(6, 2))
        themed_entry(form, textvariable=self.headcount_var).grid(row=9, column=1, sticky="ew", pady=(0, 4))

        # Portal logins tree lives in the same scroll frame as the tax form.
        _ = tree_master
        tree_card = ctk.CTkFrame(frame, corner_radius=CARD_RADIUS)
        return tree_card, frame
