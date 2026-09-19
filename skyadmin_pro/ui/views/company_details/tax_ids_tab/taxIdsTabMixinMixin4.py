from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CLIENT_CREDENTIAL_TYPES
from skyadmin_pro.ui.widgets import themed_entry


class TaxIdsTabMixinMixin4:
    def _TaxIdsTabMixin_build_cred_form(self, parent):
        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 4))
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)

        self.cred_type_var = ctk.StringVar(value=CLIENT_CREDENTIAL_TYPES[0])
        self.cred_login_var = ctk.StringVar()
        self.cred_url_var = ctk.StringVar()
        self.cred_favorite_var = ctk.BooleanVar()

        ctk.CTkLabel(form, text="Type", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
        ctk.CTkOptionMenu(form, variable=self.cred_type_var, values=list(CLIENT_CREDENTIAL_TYPES), width=120).grid(
            row=0, column=1, sticky="w", pady=2
        )
        ctk.CTkLabel(form, text="Login ID", anchor="w").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=2)
        themed_entry(form, textvariable=self.cred_login_var).grid(row=0, column=3, sticky="ew", pady=2)

        ctk.CTkLabel(form, text="Password", anchor="w").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=2)
        pw_row = ctk.CTkFrame(form, fg_color="transparent")
        pw_row.grid(row=1, column=1, columnspan=3, sticky="ew", pady=2)
        pw_row.grid_columnconfigure(0, weight=1)
        self.cred_pw_entry = themed_entry(pw_row, textvariable=self.cred_pw_var, show="*")
        self.cred_pw_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(pw_row, text="Show", width=64, command=self._toggle_client_cred_pw).grid(
            row=0, column=1, padx=(8, 0)
        )
        ctk.CTkButton(pw_row, text="Copy", width=64, command=self._copy_client_cred_password).grid(
            row=0, column=2, padx=(8, 0)
        )

        ctk.CTkLabel(form, text="Portal URL", anchor="w").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=2)
        themed_entry(form, textvariable=self.cred_url_var).grid(row=2, column=1, columnspan=3, sticky="ew", pady=2)
        self._TaxIdsTabMixin_build_cred_form_notes(form, parent)

    def _TaxIdsTabMixin_build_cred_form_notes(self, form, parent):
        ctk.CTkLabel(form, text="Notes", anchor="nw").grid(row=3, column=0, sticky="nw", padx=(0, 8), pady=2)
        self.cred_notes_box = ctk.CTkTextbox(form, height=44)
        self.cred_notes_box.grid(row=3, column=1, columnspan=3, sticky="ew", pady=2)
        ctk.CTkCheckBox(form, text="Favorite", variable=self.cred_favorite_var).grid(
            row=4, column=1, sticky="w", pady=(2, 4)
        )
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=7, column=0, sticky="w", padx=16, pady=(0, 14))
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
