from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview


class TaskPanelMixin4:
    def _TaskPanel__init__p2(self, top):
        self.columns_btn = ctk.CTkButton(
            top,
            text="⋮ Columns",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self._show_columns_menu,
        )
        self.columns_btn.pack(side="right")

        tree_card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        tree_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        tree_card.grid_columnconfigure(0, weight=1)
        tree_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            tree_card,
            text="Tasks",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.tree = ThemedTreeview(
            tree_card,
            columns=(
                ("client", "Client", 140),
                ("title", "Title", 240),
                ("category", "Category", 120),
                ("status", "Status", 90),
                ("due", "Due date", 100),
                ("completed", "Completed", 130),
            ),
            on_select=self._on_select,
            table_id="tasks",
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
        self.page_label = ctk.CTkLabel(pager, text="Page 1", text_color=TEXT_MUTED)
        self.page_label.pack(side="left", padx=10)
        return pager
