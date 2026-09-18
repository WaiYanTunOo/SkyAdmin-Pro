from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.config import COURIER_DRIVERS
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, FORM_ROW_GAP, FORM_SIDEBAR_MIN_WIDTH
from skyadmin_pro.ui.widgets import FormField, themed_scrollable_frame

from ._const_0 import FORM_PADX


class CourierPanelMixin3:
    def _CourierPanel__init__p2(self, pager):
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

        form = themed_scrollable_frame(self, corner_radius=12, width=FORM_SIDEBAR_MIN_WIDTH)
        form.grid(row=0, column=1, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Log outgoing delivery", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=FORM_PADX, pady=(14, 8)
        )

        row = 1
        self.client_field = FormField(form, label="Client", kind="combo", values=[""])
        self.client_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.client_box = self.client_field.widget
        row += 1

        self.tracking_var = ctk.StringVar()
        self.tracking_field = FormField(
            form,
            label="Tracking number",
            kind="entry",
            textvariable=self.tracking_var,
            placeholder_text="Tracking / waybill number",
        )
        self.tracking_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        row += 1

        self.driver_field = FormField(
            form, label="Driver (Grab / Lalamove)", kind="combo", values=list(COURIER_DRIVERS)
        )
        self.driver_field.set("Grab")
        self.driver_field.grid(row=row, column=0, sticky="ew", padx=FORM_PADX, pady=(FORM_ROW_GAP, 0))
        self.driver_box = self.driver_field.widget
        row += 1

        self.sent_var = ctk.StringVar(value=date.today().isoformat())
        return form, row
