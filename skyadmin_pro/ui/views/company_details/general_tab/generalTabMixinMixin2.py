from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview


class GeneralTabMixinMixin2:
    def _GeneralTabMixin_build_services_p1(self, master, tree_master=None):
        # tree_master kept for call-site compat; trees live in the scroll section.
        _ = tree_master
        section = ctk.CTkFrame(master, fg_color="transparent")
        section.grid_columnconfigure(0, weight=1)
        tree_card = ctk.CTkFrame(section, corner_radius=CARD_RADIUS)
        tree_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tree_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            tree_card,
            text="Services — expiry, payment & progress",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        # Column hide/show: ThemedTreeview built-in ⋮ Columns only (no duplicate button).
        self.service_tree = ThemedTreeview(
            tree_card,
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
            showheight=8,
            table_id="company.services",
            db=self.app.db,
        )
        self.service_tree.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        frame = ctk.CTkFrame(section, corner_radius=CARD_RADIUS)
        frame.grid(row=1, column=0, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 12))
        form.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.service_status_label = ctk.CTkLabel(form, text="New service record", text_color=TEXT_MUTED)
        self.service_status_label.grid(row=0, column=0, columnspan=4, sticky="w", pady=(4, 6))
        ctk.CTkLabel(form, text="Service type").grid(row=1, column=0, sticky="w", pady=(2, 2))
        self.service_type = ctk.CTkOptionMenu(form, values=self.app.db.list_service_types())
        self.service_type.set(self.app.db.list_service_types()[0])
        self.service_type.grid(row=2, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(form, text="Start date").grid(row=1, column=1, sticky="w", pady=(2, 2))
        self.service_start = ctk.StringVar()
        return form, section
