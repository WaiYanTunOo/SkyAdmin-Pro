from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import combo_style_kwargs


class ServicePipelinePanelMixin3:
    def _ServicePipelinePanel__init__p1(self, app, feedback):
        self.app = app
        self.feedback = feedback
        self._refresh_seq = 0
        self._page = 0
        self._page_size = 250
        self._has_more = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(top, text="Client:", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.pipe_client = ctk.CTkComboBox(top, values=[""], **combo_style_kwargs())
        self.pipe_client.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(top, text="Service:", anchor="w").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.pipe_service = ctk.CTkComboBox(
            top, values=self.app.db.list_service_types(), state="readonly", **combo_style_kwargs()
        )
        self.pipe_service.grid(row=0, column=3, sticky="ew", padx=(0, 12))
        ctk.CTkButton(top, text="Add to pipeline", width=130, command=self._add_item).grid(row=0, column=4)

        pipeline_card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        pipeline_card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        pipeline_card.grid_columnconfigure(0, weight=1)
        pipeline_card.grid_rowconfigure(2, weight=1)
        title_row = ctk.CTkFrame(pipeline_card, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            title_row,
            text="Service pipeline",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self.summary = ctk.CTkLabel(title_row, text="", text_color=TEXT_MUTED, anchor="e")
        self.summary.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.pipe_tree = ThemedTreeview(
            pipeline_card,
            columns=(
                ("client", "Client", 170),
                ("service", "Service", 220),
                ("step", "Step", 70),
                ("status", "Status", 260),
                ("updated", "Updated", 120),
            ),
            on_double_click=self._advance_item,
            table_id="pipeline",
            db=self.app.db,
        )
        return pipeline_card
