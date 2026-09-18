from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import SERVICE_PROGRESS
from skyadmin_pro.services.file_ops import format_thousands
from skyadmin_pro.ui.widgets import DatePickerField, themed_entry


class GeneralTabMixinMixin3:
    def _GeneralTabMixin_build_services_p2(self, form):
        DatePickerField(form, var=self.service_start).grid(row=2, column=1, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Expiry date").grid(row=1, column=2, sticky="w", pady=(2, 2))
        self.service_expiry = ctk.StringVar()
        DatePickerField(form, var=self.service_expiry).grid(row=2, column=2, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Payment date").grid(row=1, column=3, sticky="w", pady=(2, 2))
        self.service_payment = ctk.StringVar()
        DatePickerField(form, var=self.service_payment).grid(row=2, column=3, sticky="ew")

        ctk.CTkLabel(form, text="Amount").grid(row=3, column=0, sticky="w", pady=(10, 2))
        self.service_amount = ctk.StringVar()
        amount_entry = themed_entry(form, textvariable=self.service_amount)
        amount_entry.bind(
            "<FocusOut>",
            lambda _e: self.service_amount.set(format_thousands(self.service_amount.get())),
        )
        amount_entry.grid(row=4, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Progress").grid(row=3, column=1, sticky="w", pady=(10, 2))
        self.service_progress = ctk.CTkOptionMenu(form, values=list(SERVICE_PROGRESS))
        self.service_progress.set(SERVICE_PROGRESS[0])
        self.service_progress.grid(row=4, column=1, sticky="ew", padx=(0, 6))

        self.service_paid = ctk.CTkCheckBox(form, text="Payment received")
        self.service_paid.grid(row=3, column=2, sticky="w", pady=(10, 2))

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=4, column=2, columnspan=2, sticky="ew")
        buttons.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(buttons, text="Save service", command=self._save_service).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        self.cancel_service_btn = ctk.CTkButton(
            buttons,
            text="Cancel",
            fg_color="transparent",
            border_width=1,
            command=self._cancel_service_edit,
        )
        self.cancel_service_btn.grid(row=0, column=1, sticky="ew", padx=(2, 2))
        ctk.CTkButton(
            buttons,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete_service,
        ).grid(row=0, column=2, sticky="ew", padx=(4, 0))

        renew_buttons = ctk.CTkFrame(form, fg_color="transparent")
        renew_buttons.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        renew_buttons.grid_columnconfigure((0, 1), weight=1)
        return renew_buttons

    def _GeneralTabMixin_build_services_p3(self, renew_buttons):
        ctk.CTkButton(
            renew_buttons,
            text="Renew / extend service…",
            fg_color="transparent",
            border_width=1,
            command=self._renew_service,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            renew_buttons,
            text="Renewal history",
            fg_color="transparent",
            border_width=1,
            command=self._renewal_history,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
