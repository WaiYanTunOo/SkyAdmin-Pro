from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import FORM_ROW_GAP
from skyadmin_pro.ui.views.database_tasks.constants import NONE_TASK
from skyadmin_pro.ui.widgets import FormField

from ._const_0 import FORM_PADX


class CourierPanelMixin4:
    def _CourierPanel__init__p3(self, form, row):
        self.sent_field = FormField(form, label="Date sent", kind="date", textvariable=self.sent_var)
        self.sent_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.dest_var = ctk.StringVar()
        self.dest_field = FormField(
            form,
            label="Destination",
            kind="entry",
            textvariable=self.dest_var,
            placeholder_text="Delivery address or recipient",
        )
        self.dest_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.task_field = FormField(form, label="Related task", kind="option", values=[NONE_TASK])
        self.task_field.set(NONE_TASK)
        self.task_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.task_menu = self.task_field.widget
        row += 1

        self.notes_field = FormField(form, label="Notes", kind="textbox", height=70)
        self.notes_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        ctk.CTkButton(form, text="Log delivery", command=self._log).grid(
            row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(14, 6)
        )
        row += 1
        ctk.CTkButton(
            form,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete,
        ).grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(0, 14))

        self._task_lookup: dict[str, int] = {}
