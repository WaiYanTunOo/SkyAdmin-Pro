from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CLIENT_CREDENTIAL_TYPES
from skyadmin_pro.ui.widgets import themed_entry


class VaultTabMixinMixin4:
    def _VaultTabMixin_build_client_credentials__p2(self, form):
        self.cc_password = ctk.StringVar()
        self.cc_url = ctk.StringVar()
        self.cc_favorite = ctk.BooleanVar()
        self.cc_pw_entry: ctk.CTkEntry | None = None

        self.cc_client_menu = ctk.CTkComboBox(form, variable=self.cc_client, values=[""], width=220)
        fields = [
            ("Client company", self.cc_client_menu, 1, 0, "widget", None),
            ("Type", self.cc_type, 1, 2, "menu", CLIENT_CREDENTIAL_TYPES),
            ("Login ID / username / email", self.cc_login_id, 2, 0, "entry", None),
            ("Portal URL", self.cc_url, 2, 2, "entry", None),
        ]
        for label, var, row, col, kind, values in fields:
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=row, column=col, sticky="w", padx=16, pady=4)
            if kind == "menu":
                ctk.CTkOptionMenu(form, variable=var, values=list(values or ()), width=180).grid(
                    row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4
                )
            elif kind == "widget":
                var.grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)
            else:
                themed_entry(form, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Password", anchor="w").grid(row=3, column=0, sticky="w", padx=16, pady=4)
        pw_row = ctk.CTkFrame(form, fg_color="transparent")
        pw_row.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        pw_row.grid_columnconfigure(0, weight=1)
        self.cc_pw_entry = themed_entry(pw_row, textvariable=self.cc_password, show="*")
        self.cc_pw_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(pw_row, text="Show", width=64, command=self._toggle_client_pw).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(pw_row, text="Copy", width=64, command=self._copy_client_pw).grid(row=0, column=2, padx=(8, 0))

        ctk.CTkLabel(form, text="Notes", anchor="w").grid(row=4, column=0, sticky="nw", padx=16, pady=4)
        self.cc_notes_box = ctk.CTkTextbox(form, height=50)
        self.cc_notes_box.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkCheckBox(form, text="Favorite", variable=self.cc_favorite).grid(row=5, column=1, sticky="w")

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 12))
        ctk.CTkButton(buttons, text="Save", width=90, command=self._save_client_credential).pack(side="left")
        ctk.CTkButton(
            buttons,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._delete_client_credential,
        ).pack(side="left", padx=(8, 0))
