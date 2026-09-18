from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import OFFICE_SYSTEM_TYPES
from skyadmin_pro.ui.widgets import themed_entry


class VaultTabMixinMixin6:
    def _VaultTabMixin_build_office_credentials__p2(self, form):
        self.oc_password = ctk.StringVar()
        self.oc_type = ctk.StringVar(value=OFFICE_SYSTEM_TYPES[0])
        self.oc_url = ctk.StringVar()
        self.oc_contact = ctk.StringVar()
        self.oc_favorite = ctk.BooleanVar()
        self.oc_pw_entry: ctk.CTkEntry | None = None

        office_fields = [
            ("Account label", self.oc_label, 1, 0),
            ("Username", self.oc_login, 1, 2),
            ("Email", self.oc_email, 2, 0),
            ("System type", self.oc_type, 2, 2, True),
            ("Portal URL", self.oc_url, 3, 0),
            ("Linked contact", self.oc_contact, 3, 2),
        ]
        for item in office_fields:
            label, var, row, col = item[:4]
            is_menu = len(item) > 4 and item[4]
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=row, column=col, sticky="w", padx=16, pady=4)
            if is_menu:
                ctk.CTkOptionMenu(form, variable=var, values=list(OFFICE_SYSTEM_TYPES), width=180).grid(
                    row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4
                )
            else:
                themed_entry(form, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Password", anchor="w").grid(row=4, column=0, sticky="w", padx=16, pady=4)
        pw_row = ctk.CTkFrame(form, fg_color="transparent")
        pw_row.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        pw_row.grid_columnconfigure(0, weight=1)
        self.oc_pw_entry = themed_entry(pw_row, textvariable=self.oc_password, show="*")
        self.oc_pw_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(pw_row, text="Show", width=64, command=self._toggle_office_pw).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(pw_row, text="Copy", width=64, command=self._copy_office_pw).grid(row=0, column=2, padx=(8, 0))

        ctk.CTkLabel(form, text="Notes", anchor="w").grid(row=5, column=0, sticky="nw", padx=16, pady=4)
        self.oc_notes_box = ctk.CTkTextbox(form, height=50)
        self.oc_notes_box.grid(row=5, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkCheckBox(form, text="Favorite", variable=self.oc_favorite).grid(row=6, column=1, sticky="w")

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=7, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 12))
        ctk.CTkButton(buttons, text="Save", width=90, command=self._save_office_credential).pack(side="left")
        ctk.CTkButton(
            buttons,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._delete_office_credential,
        ).pack(side="left", padx=(8, 0))
