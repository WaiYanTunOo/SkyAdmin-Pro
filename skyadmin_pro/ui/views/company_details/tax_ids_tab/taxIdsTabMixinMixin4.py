from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CLIENT_CREDENTIAL_TYPES
from skyadmin_pro.ui.theme import FORM_LABEL_GAP, FORM_ROW_GAP
from skyadmin_pro.ui.widgets import FormField, themed_entry


class TaxIdsTabMixinMixin4:
    def _TaxIdsTabMixin_build_cred_form(self, parent):
        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.grid(row=6, column=0, sticky="ew", padx=0, pady=(0, 4))
        form.grid_columnconfigure((0, 1), weight=1)

        self.cred_type_var = ctk.StringVar(value=CLIENT_CREDENTIAL_TYPES[0])
        self.cred_login_var = ctk.StringVar()
        self.cred_url_var = ctk.StringVar()
        self.cred_favorite_var = ctk.BooleanVar()

        type_wrap = ctk.CTkFrame(form, fg_color="transparent")
        type_wrap.grid(row=0, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        type_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(type_wrap, text="Type", anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkOptionMenu(type_wrap, variable=self.cred_type_var, values=list(CLIENT_CREDENTIAL_TYPES)).grid(
            row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0)
        )

        FormField(form, label="Login ID", kind="entry", textvariable=self.cred_login_var).grid(
            row=0, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0)
        )
        self._TaxIdsTabMixin_build_cred_form_notes(form)

    def _TaxIdsTabMixin_build_cred_form_notes(self, form):
        pw_wrap = ctk.CTkFrame(form, fg_color="transparent")
        pw_wrap.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        pw_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pw_wrap, text="Password", anchor="w").grid(row=0, column=0, sticky="w")
        pw_row = ctk.CTkFrame(pw_wrap, fg_color="transparent")
        pw_row.grid(row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0))
        pw_row.grid_columnconfigure(0, weight=1)
        self.cred_pw_entry = themed_entry(pw_row, textvariable=self.cred_pw_var, show="*")
        self.cred_pw_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(pw_row, text="Show", width=64, command=self._toggle_client_cred_pw).grid(
            row=0, column=1, padx=(8, 0)
        )
        ctk.CTkButton(pw_row, text="Copy", width=64, command=self._copy_client_cred_password).grid(
            row=0, column=2, padx=(8, 0)
        )

        FormField(form, label="Portal URL", kind="entry", textvariable=self.cred_url_var).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        notes_f = FormField(form, label="Notes", kind="textbox", height=70)
        notes_f.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        self.cred_notes_box = notes_f.widget

        ctk.CTkCheckBox(form, text="Favorite", variable=self.cred_favorite_var).grid(
            row=4, column=0, sticky="w", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=5, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 14))
        ctk.CTkButton(actions, text="New", width=70, command=self._new_client_cred).pack(side="left")
        ctk.CTkButton(actions, text="Save", width=90, command=self._save_client_cred).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._delete_client_cred,
        ).pack(side="left", padx=(8, 0))
