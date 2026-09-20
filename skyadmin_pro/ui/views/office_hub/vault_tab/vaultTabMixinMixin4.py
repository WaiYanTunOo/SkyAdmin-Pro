from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CLIENT_CREDENTIAL_TYPES
from skyadmin_pro.ui.theme import FORM_LABEL_GAP, FORM_ROW_GAP
from skyadmin_pro.ui.widgets import FormField, themed_entry


class VaultTabMixinMixin4:
    def _VaultTabMixin_build_client_credentials__p2(self, form):
        self.cc_password = ctk.StringVar()
        self.cc_url = ctk.StringVar()
        self.cc_favorite = ctk.BooleanVar()
        self.cc_pw_entry: ctk.CTkEntry | None = None

        client_f = FormField(form, label="Client company", kind="entry", textvariable=self.cc_client)
        client_f.grid(row=1, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        client_f.widget.configure(state="disabled")
        self.cc_client_menu = client_f.widget  # refresh hook expects .configure(values=…)

        type_wrap = ctk.CTkFrame(form, fg_color="transparent")
        type_wrap.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0))
        type_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(type_wrap, text="Type", anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkOptionMenu(
            type_wrap, variable=self.cc_type, values=list(CLIENT_CREDENTIAL_TYPES), state="disabled"
        ).grid(row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0))

        login_f = FormField(form, label="Login ID / username / email", kind="entry", textvariable=self.cc_login_id)
        login_f.grid(row=2, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        login_f.widget.configure(state="disabled")
        url_f = FormField(form, label="Portal URL", kind="entry", textvariable=self.cc_url)
        url_f.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0))
        url_f.widget.configure(state="disabled")

        pw_wrap = ctk.CTkFrame(form, fg_color="transparent")
        pw_wrap.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        pw_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pw_wrap, text="Password", anchor="w").grid(row=0, column=0, sticky="w")
        pw_row = ctk.CTkFrame(pw_wrap, fg_color="transparent")
        pw_row.grid(row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0))
        pw_row.grid_columnconfigure(0, weight=1)
        self.cc_pw_entry = themed_entry(pw_row, textvariable=self.cc_password, show="*", state="disabled")
        self.cc_pw_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(pw_row, text="Show", width=64, command=self._toggle_client_pw).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(pw_row, text="Copy", width=64, command=self._copy_client_pw).grid(row=0, column=2, padx=(8, 0))

        notes_f = FormField(form, label="Notes", kind="textbox", height=70)
        notes_f.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        self.cc_notes_box = notes_f.widget
        self.cc_notes_box.configure(state="disabled")
        ctk.CTkCheckBox(form, text="Favorite", variable=self.cc_favorite, state="disabled").grid(
            row=5, column=0, sticky="w", padx=16, pady=(FORM_ROW_GAP, 12)
        )
