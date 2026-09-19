from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, form_sidebar_min_width
from skyadmin_pro.ui.treeview import ThemedTreeview


class CourierPanelMixin2:
    def _CourierPanel__init__p1(self, app, feedback):
        self.app = app
        self.feedback = feedback
        self._refresh_seq = 0
        self._page = 0
        self._page_size = 250
        self._has_more = False
        self._form_sidebar_min = form_sidebar_min_width()
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=self._form_sidebar_min)
        self.grid_rowconfigure(0, weight=1)

        tree_card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        tree_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tree_card.grid_columnconfigure(0, weight=1)
        tree_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            tree_card,
            text="Courier deliveries",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.tree = ThemedTreeview(
            tree_card,
            columns=(
                ("sent", "Date sent", 110),
                ("client", "Client", 140),
                ("tracking", "Tracking no.", 160),
                ("driver", "Driver", 110),
                ("destination", "Destination", 160),
                ("task", "Related task", 160),
            ),
            table_id="courier",
            db=self.app.db,
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 4))

        pager = ctk.CTkFrame(tree_card, fg_color="transparent")
        pager.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.prev_btn = ctk.CTkButton(
            pager,
            text="◀ Prev",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._prev_page,
        )
        self.prev_btn.pack(side="left")
        self.page_label = ctk.CTkLabel(pager, text="Page 1", text_color="gray")
        self.page_label.pack(side="left", padx=10)
        return pager
