from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.widgets import combo_style_kwargs, themed_scrollable_frame


class RenewalPanelMixin3:
    def _RenewalPanel__init__p1(self, app, feedback):
        self.app = app
        self.feedback = feedback
        self._refresh_seq = 0
        self._checkboxes: dict[int, ctk.CTkCheckBox] = {}
        self._services: list[dict] = []
        self._service_by_value: dict[str, dict] = {}
        self._template: str = "Visa Renewal"
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        selector = ctk.CTkFrame(self, fg_color="transparent")
        selector.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        selector.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(selector, text="Company / Client:", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.company_box = ctk.CTkComboBox(selector, values=[""], command=self._on_company, **combo_style_kwargs())
        self.company_box.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(selector, text="Service:", anchor="w").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        self.service_box = ctk.CTkComboBox(
            selector,
            values=[""],
            command=self._on_service,
            state="readonly",
            **combo_style_kwargs(),
        )
        self.service_box.grid(row=1, column=1, sticky="ew", pady=(8, 0))

        card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)
        self.checklist_title = ctk.CTkLabel(
            header,
            text="Renewal document checklist",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        )
        self.checklist_title.grid(row=0, column=0, sticky="w")
        self.progress_label = ctk.CTkLabel(header, text="0 of 0", text_color=TEXT_MUTED, anchor="e")
        self.progress_label.grid(row=0, column=1, sticky="e")
        self.countdown = ctk.CTkLabel(
            card,
            text="Checklist only. Edit the expiry date in Company Details → General.",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.countdown.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        self.progress_bar = ctk.CTkProgressBar(card)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))
        return card

    def _RenewalPanel__init__p2(self, card):
        self.scroll = themed_scrollable_frame(card)
        self.scroll.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.scroll.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))
        ctk.CTkButton(
            footer,
            text="Reset checklist",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._reset_all,
        ).pack(side="left")
        ctk.CTkLabel(
            footer,
            text="Tick items as they arrive; the bar shows overall readiness.",
            text_color=TEXT_MUTED,
        ).pack(side="right")

        self._renewals_tree = None
