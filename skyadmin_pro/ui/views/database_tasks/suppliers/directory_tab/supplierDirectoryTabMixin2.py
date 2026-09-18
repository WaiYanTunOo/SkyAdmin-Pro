from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry


class SupplierDirectoryTabMixin2:
    def _SupplierDirectoryTab__init__p1(self, host, master):
        self.host = host
        self.app = host.app
        self.feedback = host.feedback
        self.selected_supplier_id: int | None = None
        self.on_supplier_selected: Callable[[int | None], None] | None = None

        # Form stays on the card; the tree sits below it and takes leftover height.
        card = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(
            card,
            text="Vendors we owe",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure(1, weight=1, uniform="sup_field")
        form.grid_columnconfigure(3, weight=1, uniform="sup_field")
        ctk.CTkLabel(form, text="Name").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.sup_name = themed_entry(form, placeholder_text="Required")
        self.sup_name.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Company").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.sup_company = themed_entry(form)
        self.sup_company.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Contact").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.sup_contact = themed_entry(form)
        self.sup_contact.grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Notes").grid(row=2, column=0, sticky="nw", padx=(0, 8), pady=4)
        self.sup_notes = ctk.CTkTextbox(form, height=100)
        self.sup_notes.grid(row=2, column=1, columnspan=3, sticky="ew", pady=4)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        ctk.CTkButton(btns, text="Save", width=100, command=self._save_supplier).pack(side="left")
        ctk.CTkButton(
            btns,
            text="New",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._new_supplier,
        ).pack(side="left", padx=(8, 0))
        return card

    def _SupplierDirectoryTab__init__p2(self, card):
        self.supplier_tree = ThemedTreeview(
            card,
            columns=(
                ("name", "Name", 160),
                ("company", "Company", 140),
                ("contact", "Contact", 150),
                ("notes", "Notes", 260),
            ),
            on_select=self._on_supplier_select,
            showheight=8,
            table_id="suppliers.directory",
            db=self.app.db,
        )
        self.supplier_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        ctk.CTkButton(
            card,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete_supplier,
        ).grid(row=4, column=0, sticky="w", padx=16, pady=(0, 14))
