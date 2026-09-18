from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview


class GeneralTabMixinMixin2:
    def _GeneralTabMixin_build_services_p1(self, master):
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=0)
        ctk.CTkLabel(
            frame,
            text="Services — expiry, payment & progress",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.svc_columns_btn = ctk.CTkButton(
            frame,
            text="⋮ Columns",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self._show_service_columns_menu,
        )
        self.svc_columns_btn.grid(row=0, column=1, sticky="e", padx=(0, 16), pady=(14, 8))

        self.service_tree = ThemedTreeview(
            frame,
            columns=(
                ("type", "Service", 150),
                ("start", "Start", 95),
                ("expiry", "Expiry", 95),
                ("payment", "Payment", 95),
                ("amount", "Amount", 85),
                ("progress", "Progress", 95),
                ("paid", "Paid", 55),
            ),
            on_double_click=self._edit_service,
            table_id="company.services",
            db=self.app.db,
        )
        self.service_tree.tree.configure(height=8)
        self.service_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        form.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.service_status_label = ctk.CTkLabel(form, text="New service record", text_color=TEXT_MUTED)
        self.service_status_label.grid(row=0, column=0, columnspan=4, sticky="w", pady=(4, 6))

        ctk.CTkLabel(form, text="Service type").grid(row=1, column=0, sticky="w", pady=(2, 2))
        self.service_type = ctk.CTkOptionMenu(form, values=self.app.db.list_service_types())
        self.service_type.set(self.app.db.list_service_types()[0])
        self.service_type.grid(row=2, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Start date").grid(row=1, column=1, sticky="w", pady=(2, 2))
        self.service_start = ctk.StringVar()
        return form, frame
