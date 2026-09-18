from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import DOCUMENT_TYPES
from skyadmin_pro.services import file_ops
from skyadmin_pro.ui.widgets import DatePickerField, themed_entry


class SmartRenamerPanelMixin3:
    def _SmartRenamerPanel__init__p2(self, body):
        self.client_box = ctk.CTkComboBox(
            body,
            variable=self.client_var,
            values=[""],
            command=lambda _: self._schedule_preview(),
        )
        self.client_box.grid(row=1, column=0, sticky="ew", padx=16)
        self.client_var.trace_add("write", lambda *_: self._schedule_preview())

        ctk.CTkLabel(body, text="Document type", anchor="w").grid(row=2, column=0, sticky="w", padx=16, pady=(14, 4))
        self.type_menu = ctk.CTkOptionMenu(
            body,
            values=list(DOCUMENT_TYPES),
            command=self._on_type_change,
        )
        self.type_menu.grid(row=3, column=0, sticky="ew", padx=16)
        self.type_menu.set(DOCUMENT_TYPES[0])

        self.invoice_wrap = ctk.CTkFrame(body, fg_color="transparent")
        self.invoice_wrap.grid(row=4, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.invoice_wrap.grid_columnconfigure(0, weight=1)
        self.invoice_sop = ctk.CTkCheckBox(
            self.invoice_wrap,
            text="SOP invoice naming: YYYYMM_Client_Invoice_INV…",
            command=self._update_preview,
        )
        self.invoice_sop.grid(row=0, column=0, sticky="w")

        self.expiry_wrap = ctk.CTkFrame(body, fg_color="transparent")
        self.expiry_wrap.grid(row=5, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.expiry_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.expiry_wrap, text="Expiry date", anchor="w").grid(row=0, column=0, sticky="w")
        self.expiry_var = ctk.StringVar()
        DatePickerField(self.expiry_wrap, var=self.expiry_var).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.expiry_var.trace_add("write", lambda *_: self._schedule_preview())

        self.amount_wrap = ctk.CTkFrame(body, fg_color="transparent")
        self.amount_wrap.grid(row=6, column=0, sticky="ew", padx=16, pady=(14, 0))
        self.amount_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.amount_wrap, text="Amount", anchor="w").grid(row=0, column=0, sticky="w")
        self.amount_var = ctk.StringVar()
        amount_entry = themed_entry(
            self.amount_wrap,
            textvariable=self.amount_var,
            placeholder_text="e.g. 15000",
        )
        amount_entry.bind(
            "<FocusOut>",
            lambda _e: self.amount_var.set(file_ops.format_thousands(self.amount_var.get())),
        )
        amount_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.amount_var.trace_add("write", lambda *_: self._schedule_preview())
