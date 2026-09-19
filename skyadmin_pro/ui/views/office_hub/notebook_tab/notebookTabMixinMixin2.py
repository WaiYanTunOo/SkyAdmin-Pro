from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.config import NOTEBOOK_ENTRY_TYPES
from skyadmin_pro.ui.theme import FORM_LABEL_GAP, FORM_ROW_GAP
from skyadmin_pro.ui.widgets import FormField


class NotebookTabMixinMixin2:
    def _NotebookTabMixin_build_notebook_tab_p2(self, form):
        self.n_title = ctk.StringVar()
        self.n_date = ctk.StringVar(value=date.today().isoformat())
        self.n_author = ctk.StringVar()
        self.n_client = ctk.StringVar()
        self.n_follow = ctk.StringVar()
        self.n_pinned = ctk.BooleanVar()

        type_wrap = ctk.CTkFrame(form, fg_color="transparent")
        type_wrap.grid(row=1, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        type_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(type_wrap, text="Type", anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkOptionMenu(type_wrap, variable=self.n_type, values=[lbl for _k, lbl in NOTEBOOK_ENTRY_TYPES]).grid(
            row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0)
        )

        FormField(form, label="Title", kind="entry", textvariable=self.n_title).grid(
            row=1, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0)
        )
        FormField(form, label="Date", kind="entry", textvariable=self.n_date).grid(
            row=2, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        FormField(form, label="Author / from", kind="entry", textvariable=self.n_author).grid(
            row=2, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0)
        )
        FormField(form, label="Linked client", kind="entry", textvariable=self.n_client).grid(
            row=3, column=0, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0)
        )
        FormField(form, label="Follow-up date", kind="entry", textvariable=self.n_follow).grid(
            row=3, column=1, sticky="ew", padx=(0, 16), pady=(FORM_ROW_GAP, 0)
        )

        body_f = FormField(form, label="Body", kind="textbox", height=120)
        body_f.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(FORM_ROW_GAP, 0))
        self.n_body_box = body_f.widget

        ctk.CTkCheckBox(form, text="Pin to top", variable=self.n_pinned).grid(
            row=5, column=0, sticky="w", padx=16, pady=(FORM_ROW_GAP, 0)
        )

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 14))
        ctk.CTkButton(buttons, text="Save note", width=110, command=self._save_note).pack(side="left")
        ctk.CTkButton(
            buttons, text="Delete", width=90, fg_color="transparent", border_width=1, command=self._delete_note
        ).pack(side="left", padx=(12, 0))

        self._note_from_date: str | None = None
        self._note_to_date: str | None = None
