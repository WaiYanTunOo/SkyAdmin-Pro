from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CONTACT_CATEGORIES
from skyadmin_pro.ui.widgets import themed_entry


class ContactsTabMixinMixin3:
    def _ContactsTabMixin_build_contacts_tab_p2(self, form):
        self.c_favorite = ctk.BooleanVar()

        self.c_org_menu = ctk.CTkComboBox(form, variable=self.c_org, values=[""], width=220)
        self.c_dept_menu = ctk.CTkComboBox(form, variable=self.c_dept, values=[""], width=220)
        self.c_client_menu = ctk.CTkComboBox(form, variable=self.c_client, values=[""], width=220)

        simple_fields = [
            ("Name", self.c_name, 1, 0),
            ("Role", self.c_role, 1, 2),
            ("Phone", self.c_phone, 3, 0),
            ("Email", self.c_email, 3, 2),
            ("LINE ID", self.c_line, 4, 0),
        ]
        for label, var, row, col in simple_fields:
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=row, column=col, sticky="w", padx=16, pady=4)
            themed_entry(form, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Company", anchor="w").grid(row=2, column=0, sticky="w", padx=16, pady=4)
        self.c_org_menu.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkLabel(form, text="Department", anchor="w").grid(row=2, column=2, sticky="w", padx=16, pady=4)
        self.c_dept_menu.grid(row=2, column=3, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Category", anchor="w").grid(row=4, column=2, sticky="w", padx=16, pady=4)
        ctk.CTkOptionMenu(form, variable=self.c_category, values=list(CONTACT_CATEGORIES), width=180).grid(
            row=4, column=3, sticky="ew", padx=(0, 16), pady=4
        )
        ctk.CTkLabel(form, text="Linked client", anchor="w").grid(row=5, column=0, sticky="w", padx=16, pady=4)
        self.c_client_menu.grid(row=5, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Notes", anchor="w").grid(row=6, column=0, sticky="nw", padx=16, pady=4)
        self.c_notes_box = ctk.CTkTextbox(form, height=70)
        self.c_notes_box.grid(row=6, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkCheckBox(form, text="Favorite", variable=self.c_favorite).grid(row=7, column=1, sticky="w", pady=4)

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=8, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 14))
        ctk.CTkButton(buttons, text="Save contact", width=120, command=self._save_contact).pack(side="left")
        ctk.CTkButton(
            buttons, text="Delete", width=90, fg_color="transparent", border_width=1, command=self._delete_contact
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            buttons,
            text="Copy phone",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._copy_contact_phone,
        ).pack(side="left", padx=(8, 0))
