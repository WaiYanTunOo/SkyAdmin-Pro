from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import TASK_CATEGORIES
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, FORM_ROW_GAP, TEXT_MUTED, form_sidebar_min_width
from skyadmin_pro.ui.widgets import FormField, themed_scrollable_frame

from ._const_0 import FORM_PADX


class TaskPanelMixin5:
    def _TaskPanel__init__p3(self, pager):
        self.next_btn = ctk.CTkButton(
            pager,
            text="Next ▶",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._next_page,
        )
        self.next_btn.pack(side="left")
        self.page_size_menu = ctk.CTkOptionMenu(
            pager,
            values=["100", "250", "500", "1000"],
            width=90,
            command=self._on_page_size,
        )
        self.page_size_menu.set("250")
        self.page_size_menu.pack(side="right")

        form_w = getattr(self, "_form_sidebar_min", form_sidebar_min_width())
        form = themed_scrollable_frame(self, corner_radius=12, width=form_w)
        self._task_form = form
        form.grid(row=1, column=1, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Task details", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=FORM_PADX, pady=(14, 8)
        )
        self.status_label = ctk.CTkLabel(form, text="Status: new", text_color=TEXT_MUTED)
        self.status_label.grid(row=1, column=0, sticky="w", padx=FORM_PADX)

        row = 2
        self.client_field = FormField(form, label="Client", kind="combo", values=[""])
        self.client_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.client_box = self.client_field.widget
        row += 1

        self.title_var = ctk.StringVar()
        self.title_field = FormField(
            form,
            label="Title",
            kind="entry",
            textvariable=self.title_var,
            placeholder_text="Task title",
        )
        self.title_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.category_field = FormField(form, label="Category", kind="option", values=list(TASK_CATEGORIES))
        self.category_field.set("General")
        self.category_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.category_menu = self.category_field.widget
        row += 1

        self.due_var = ctk.StringVar()
        return form, row

    def _TaskPanel__init__p4(self, form, row):
        self.due_field = FormField(form, label="Due date", kind="date", textvariable=self.due_var)
        self.due_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.notes_field = FormField(form, label="Notes", kind="textbox", height=90)
        self.notes_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.notes = self.notes_field.widget
        row += 1

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(14, 14))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="New", command=self._new).grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
        ctk.CTkButton(buttons, text="Save", command=self._save).grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=3)
        ctk.CTkButton(buttons, text="Mark complete", command=self._complete).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=3
        )
        ctk.CTkButton(
            buttons,
            text="Reopen",
            fg_color="transparent",
            border_width=1,
            command=self._reopen,
        ).grid(row=2, column=0, sticky="ew", padx=(0, 4), pady=3)
        ctk.CTkButton(
            buttons,
            text="Delete",
            fg_color="transparent",
            border_width=1,
            command=self._delete,
        ).grid(row=2, column=1, sticky="ew", padx=(4, 0), pady=3)
