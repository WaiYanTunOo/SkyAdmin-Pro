from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField


class ClientsExpiryPanelMixin0Mixin4:
    def _ClientsExpiryPanelMixin0__init__p5(self, batch_row):
        ctk.CTkButton(
            batch_row,
            text="Mark Active",
            width=95,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._batch_set_status("active"),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row,
            text="Mark Inactive",
            width=95,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._batch_set_status("inactive"),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row,
            text="Assign group…",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._batch_assign_group,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row,
            text="Undo",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._undo_last,
        ).pack(side="left")

        right = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(
            right,
            text="Register document / service expiry",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(right, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(form, text="Client").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.expiry_client = ctk.CTkComboBox(form, values=[""])
        self.expiry_client.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Type").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.expiry_type = ctk.CTkOptionMenu(form, values=self.app.db.list_service_types())
        self.expiry_type.set(self.app.db.list_service_types()[0])
        return form, right

    def _ClientsExpiryPanelMixin0__init__p6(self, form, right):
        self.expiry_type.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Expiry").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.expiry_var = ctk.StringVar()
        DatePickerField(form, var=self.expiry_var).grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkButton(right, text="Save expiry record", command=self._add_expiry).grid(
            row=2, column=0, sticky="ew", padx=16, pady=(8, 8)
        )

        self.doc_tree = ThemedTreeview(
            right,
            columns=(
                ("client", "Client", 140),
                ("type", "Type", 190),
                ("expiry", "Expiry", 100),
                ("days", "Days left", 120),
                ("status", "Status", 200),
            ),
            showheight=8,
            table_id="clients.expiry",
            db=self.app.db,
        )
        self.doc_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        ctk.CTkButton(
            right,
            text="Delete selected record",
            fg_color="transparent",
            border_width=1,
            command=self._delete_document,
        ).grid(row=4, column=0, sticky="w", padx=16, pady=(0, 14))
