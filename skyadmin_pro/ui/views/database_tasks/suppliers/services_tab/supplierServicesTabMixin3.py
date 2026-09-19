from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE
from skyadmin_pro.ui.widgets import DatePickerField, combo_style_kwargs, themed_entry


class SupplierServicesTabMixin3:
    def _SupplierServicesTab__init__p1(self, host, master):
        self.host = host
        self.app = host.app
        self.feedback = host.feedback
        self._editing_svc_id: int | None = None

        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)
        svc_card = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        svc_card.grid(row=0, column=0, sticky="nsew")
        svc_card.grid_columnconfigure(0, weight=1)
        svc_card.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            svc_card,
            text="Supplier services — tracked per supplier",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            svc_card,
            text="Select a supplier in the Suppliers tab first, then add services here.",
            text_color=("gray40", "gray60"),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        svc_form = ctk.CTkFrame(svc_card, fg_color="transparent")
        svc_form.grid(row=2, column=0, sticky="ew", padx=16)
        svc_form.grid_columnconfigure(1, weight=1)
        svc_form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(svc_form, text="Company").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.svc_company = ctk.CTkComboBox(svc_form, values=[""], state="readonly", **combo_style_kwargs())
        self.svc_company.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(svc_form, text="Service").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.svc_service = ctk.CTkComboBox(svc_form, values=[""], state="readonly", **combo_style_kwargs())
        self.svc_service.grid(row=0, column=3, sticky="ew", pady=4)
        self._refresh_svc_combos()
        ctk.CTkLabel(svc_form, text="Expiry date").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.svc_expiry_var = ctk.StringVar()
        DatePickerField(svc_form, var=self.svc_expiry_var).grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(svc_form, text="Notes").grid(row=1, column=2, sticky="w", padx=(12, 8), pady=4)
        self.svc_notes = themed_entry(svc_form, placeholder_text="Optional")
        self.svc_notes.grid(row=1, column=3, sticky="ew", pady=4)

        svc_btns = ctk.CTkFrame(svc_card, fg_color="transparent")
        svc_btns.grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 4))
        ctk.CTkButton(svc_btns, text="Add service", width=110, command=self._add_supplier_service).pack(side="left")
        return svc_btns, svc_card
