from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.config import COURIER_DRIVERS
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, FORM_ROW_GAP, form_sidebar_min_width
from skyadmin_pro.ui.widgets import FormField, themed_scrollable_frame

from ._const_0 import FORM_PADX


class CourierPanelMixin3:
    def _apply_responsive_layout(self, *, form_sidebar_min: int, metrics=None) -> None:
        self._form_sidebar_min = form_sidebar_min
        self.grid_columnconfigure(1, weight=0, minsize=form_sidebar_min)
        form = getattr(self, "_courier_form", None)
        if form is not None:
            try:
                form.configure(width=form_sidebar_min)
            except Exception as e:
                import logging

                logging.error(f"UI Error: {e}")

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
        ctk.CTkLabel(pager, text="Per page", text_color="gray").pack(side="right", padx=(8, 4))
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
        self._courier_form = form
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
