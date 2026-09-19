"""Shared host so a moved panel fills a sidebar page. Does not copy panel logic."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_CONTENT_PADX, CARD_RADIUS, card_style_kwargs
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import FeedbackLabel


class PanelHostView(BaseView):
    # Nested inset inside the page card. Subclasses may set 0 for edge-to-edge tabs.
    panel_inset = CARD_CONTENT_PADX

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)
        self.feedback = FeedbackLabel(self.body)
        self.feedback.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        # Body already uses CONTENT_PAD. This card is the page fill.
        card = ctk.CTkFrame(self.body, corner_radius=CARD_RADIUS, **card_style_kwargs())
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        self.panel_parent = card
        self.panel = self._make_panel()
        inset = int(getattr(self, "panel_inset", CARD_CONTENT_PADX) or 0)
        self.panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=inset,
            pady=inset,
        )

    def _make_panel(self) -> ctk.CTkFrame:
        raise NotImplementedError

    def on_show(self) -> None:
        refresh = getattr(self.panel, "refresh", None)
        if callable(refresh):
            refresh()
