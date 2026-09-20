from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import OFFICE_SYSTEM_TYPES
from skyadmin_pro.ui.theme import FORM_LABEL_GAP, FORM_ROW_GAP
from skyadmin_pro.ui.widgets import FormField, themed_entry


class VaultTabMixinMixin6:
    def _VaultTabMixin_build_office_credentials__p2(self, form):
        self.oc_password = ctk.StringVar()
        self.oc_type = ctk.StringVar(value=OFFICE_SYSTEM_TYPES[0])
        self.oc_url = ctk.StringVar()
        self.oc_contact = ctk.StringVar()
        self.oc_favorite = ctk.BooleanVar()
        self.oc_pw_entry: ctk.CTkEntry | None = None

        FormField(form, label="Account label", kind="entry", textvariable=self.oc_label).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        FormField(form, label="Username", kind="entry", textvariable=self.oc_login).grid(
            row=1, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0)
        )
        FormField(form, label="Email", kind="entry", textvariable=self.oc_email).grid(
            row=2, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        type_wrap = ctk.CTkFrame(form, fg_color="transparent")
        type_wrap.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0))
        type_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(type_wrap, text="System type", anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkOptionMenu(type_wrap, variable=self.oc_type, values=list(OFFICE_SYSTEM_TYPES)).grid(
            row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0)
        )
        FormField(form, label="Portal URL", kind="entry", textvariable=self.oc_url).grid(
            row=3, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        contact_wrap = ctk.CTkFrame(form, fg_color="transparent")
        contact_wrap.grid(row=3, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0))
        contact_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(contact_wrap, text="Linked contact", anchor="w").grid(row=0, column=0, sticky="w")
        self.oc_contact_menu = ctk.CTkComboBox(contact_wrap, variable=self.oc_contact, values=[""])
        self.oc_contact_menu.grid(row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0))

        pw_wrap = ctk.CTkFrame(form, fg_color="transparent")
        pw_wrap.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        pw_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pw_wrap, text="Password", anchor="w").grid(row=0, column=0, sticky="w")
        pw_row = ctk.CTkFrame(pw_wrap, fg_color="transparent")
        pw_row.grid(row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0))
        pw_row.grid_columnconfigure(0, weight=1)
        self.oc_pw_entry = themed_entry(pw_row, textvariable=self.oc_password, show="*")
        self.oc_pw_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(pw_row, text="Show", width=64, command=self._toggle_office_pw).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(pw_row, text="Copy", width=64, command=self._copy_office_pw).grid(row=0, column=2, padx=(8, 0))

        notes_f = FormField(form, label="Notes", kind="textbox", height=70)
        notes_f.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        self.oc_notes_box = notes_f.widget
        ctk.CTkCheckBox(form, text="Favorite", variable=self.oc_favorite).grid(
            row=6, column=0, sticky="w", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=7, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 14))
        ctk.CTkButton(buttons, text="Save", width=100, command=self._save_office_credential).pack(side="left")
        ctk.CTkButton(
            buttons,
            text="Delete",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self._delete_office_credential,
        ).pack(side="left", padx=(12, 0))
