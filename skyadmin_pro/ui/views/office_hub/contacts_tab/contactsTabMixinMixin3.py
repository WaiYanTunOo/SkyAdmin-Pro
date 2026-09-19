from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CONTACT_CATEGORIES
from skyadmin_pro.ui.theme import FORM_LABEL_GAP, FORM_ROW_GAP
from skyadmin_pro.ui.widgets import FormField


class ContactsTabMixinMixin3:
    def _ContactsTabMixin_build_contacts_tab_p2(self, form):
        self.c_favorite = ctk.BooleanVar()

        FormField(form, label="Name", kind="entry", textvariable=self.c_name).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        FormField(form, label="Role", kind="entry", textvariable=self.c_role).grid(
            row=1, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0)
        )

        org_wrap = ctk.CTkFrame(form, fg_color="transparent")
        org_wrap.grid(row=2, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        org_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(org_wrap, text="Company", anchor="w").grid(row=0, column=0, sticky="w")
        self.c_org_menu = ctk.CTkComboBox(org_wrap, variable=self.c_org, values=[""])
        self.c_org_menu.grid(row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0))

        dept_wrap = ctk.CTkFrame(form, fg_color="transparent")
        dept_wrap.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0))
        dept_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(dept_wrap, text="Department", anchor="w").grid(row=0, column=0, sticky="w")
        self.c_dept_menu = ctk.CTkComboBox(dept_wrap, variable=self.c_dept, values=[""])
        self.c_dept_menu.grid(row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0))

        FormField(form, label="Phone", kind="entry", textvariable=self.c_phone).grid(
            row=3, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        FormField(form, label="Email", kind="entry", textvariable=self.c_email).grid(
            row=3, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0)
        )
        FormField(form, label="LINE ID", kind="entry", textvariable=self.c_line).grid(
            row=4, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        cat_wrap = ctk.CTkFrame(form, fg_color="transparent")
        cat_wrap.grid(row=4, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0))
        cat_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cat_wrap, text="Category", anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkOptionMenu(cat_wrap, variable=self.c_category, values=list(CONTACT_CATEGORIES)).grid(
            row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0)
        )

        client_wrap = ctk.CTkFrame(form, fg_color="transparent")
        client_wrap.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        client_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(client_wrap, text="Linked client", anchor="w").grid(row=0, column=0, sticky="w")
        self.c_client_menu = ctk.CTkComboBox(client_wrap, variable=self.c_client, values=[""])
        self.c_client_menu.grid(row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0))

        notes_f = FormField(form, label="Notes", kind="textbox", height=70)
        notes_f.grid(row=6, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        self.c_notes_box = notes_f.widget

        ctk.CTkCheckBox(form, text="Favorite", variable=self.c_favorite).grid(
            row=7, column=0, sticky="w", padx=16, pady=(FORM_ROW_GAP, 0)
        )

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=8, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 14))
        ctk.CTkButton(buttons, text="Save contact", width=120, command=self._save_contact).pack(side="left")
        ctk.CTkButton(
            buttons, text="Delete", width=90, fg_color="transparent", border_width=1, command=self._delete_contact
        ).pack(side="left", padx=(12, 0))
        ctk.CTkButton(
            buttons,
            text="Copy phone",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._copy_contact_phone,
        ).pack(side="left", padx=(12, 0))
