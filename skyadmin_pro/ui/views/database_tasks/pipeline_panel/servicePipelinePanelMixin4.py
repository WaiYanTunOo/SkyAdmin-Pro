from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import PIPELINE_STEPS
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.widgets import bind_wrap_label


class ServicePipelinePanelMixin4:
    def _ServicePipelinePanel__init__p2(self, pipeline_card):
        self.pipe_tree.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 4))

        pager = ctk.CTkFrame(pipeline_card, fg_color="transparent")
        pager.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
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

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew")
        controls.grid_columnconfigure(4, weight=1)
        ctk.CTkLabel(controls, text="Set step:").grid(row=0, column=0, sticky="w")
        self.step_menu = ctk.CTkOptionMenu(
            controls,
            values=list(PIPELINE_STEPS),
        )
        self.step_menu.set(PIPELINE_STEPS[0])
        self.step_menu.grid(row=0, column=1, sticky="w", padx=(4, 8))
        ctk.CTkButton(controls, text="Apply", width=70, command=self._set_step).grid(row=0, column=2)
        ctk.CTkButton(controls, text="Advance step", width=120, command=self._advance_item).grid(
            row=0, column=3, padx=(8, 0)
        )
        return controls

    def _ServicePipelinePanel__init__p3(self, controls):
        ctk.CTkButton(
            controls,
            text="Delete",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._delete_item,
        ).grid(row=0, column=5, padx=(8, 0))
        hint = ctk.CTkLabel(
            controls,
            text="Double-click a row to advance. Steps 3 and 7 are the money milestones.",
            text_color=TEXT_MUTED,
            anchor="e",
            justify="right",
        )
        hint.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(6, 0))
        bind_wrap_label(hint, controls, pad=16)
