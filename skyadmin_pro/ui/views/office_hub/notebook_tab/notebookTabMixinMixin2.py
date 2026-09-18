from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.config import NOTEBOOK_ENTRY_TYPES
from skyadmin_pro.ui.widgets import themed_entry


class NotebookTabMixinMixin2:
    def _NotebookTabMixin_build_notebook_tab_p2(self, form):
        self.n_title = ctk.StringVar()
        self.n_date = ctk.StringVar(value=date.today().isoformat())
        self.n_author = ctk.StringVar()
        self.n_client = ctk.StringVar()
        self.n_follow = ctk.StringVar()
        self.n_pinned = ctk.BooleanVar()

        note_fields = [
            ("Type", self.n_type, 1, 0, "menu"),
            ("Title", self.n_title, 1, 2, "entry"),
            ("Date", self.n_date, 2, 0, "entry"),
            ("Author / from", self.n_author, 2, 2, "entry"),
            ("Linked client", self.n_client, 3, 0, "entry"),
            ("Follow-up date", self.n_follow, 3, 2, "entry"),
        ]
        for label, var, row, col, kind in note_fields:
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=row, column=col, sticky="w", padx=16, pady=4)
            if kind == "menu":
                ctk.CTkOptionMenu(form, variable=var, values=[lbl for _k, lbl in NOTEBOOK_ENTRY_TYPES], width=200).grid(
                    row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4
                )
            else:
                themed_entry(form, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Body", anchor="w").grid(row=4, column=0, sticky="nw", padx=16, pady=4)
        self.n_body_box = ctk.CTkTextbox(form, height=120)
        self.n_body_box.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkCheckBox(form, text="Pin to top", variable=self.n_pinned).grid(row=5, column=1, sticky="w", pady=4)

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 14))
        ctk.CTkButton(buttons, text="Save note", width=110, command=self._save_note).pack(side="left")
        ctk.CTkButton(
            buttons, text="Delete", width=90, fg_color="transparent", border_width=1, command=self._delete_note
        ).pack(side="left", padx=(8, 0))

        self._note_from_date: str | None = None
        self._note_to_date: str | None = None
