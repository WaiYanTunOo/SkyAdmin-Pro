from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from skyadmin_pro.ui.theme import CANVAS_BG, CARD_TITLE_SIZE
from skyadmin_pro.ui.widgets import themed_entry


class DashboardViewMixin8:
    def _DashboardView_build_header_extras_p1(self):
        self._header_extras_built = True

        timeline_card = ctk.CTkFrame(self._today, corner_radius=12)
        timeline_card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        timeline_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            timeline_card,
            text="Expiry Timeline — next 45 days",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        self.timeline_canvas = tk.Canvas(
            timeline_card,
            height=120,
            bg=CANVAS_BG[1 if ctk.get_appearance_mode() == "Dark" else 0],
            highlightthickness=0,
        )
        self.timeline_canvas.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self._timeline_resize_after: str | None = None

        def _on_timeline_resize(_event=None) -> None:
            if self._timeline_resize_after:
                try:
                    self.after_cancel(self._timeline_resize_after)
                except Exception as e:
                    import logging

                    logging.error(f"UI Error: {e}")
                self._timeline_resize_after = None

            def _redraw() -> None:
                self._timeline_resize_after = None
                if self._visible:
                    self._draw_timeline()

            self._timeline_resize_after = self.after(150, _redraw)

        self.timeline_canvas.bind("<Configure>", _on_timeline_resize)

        workflow = ctk.CTkFrame(self._today, corner_radius=12)
        workflow.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        workflow.grid_columnconfigure(1, weight=1)

        self.onboard_var = ctk.StringVar()
        themed_entry(
            workflow,
            textvariable=self.onboard_var,
            placeholder_text="New client name",
        ).grid(row=0, column=1, padx=(8, 8), pady=14, sticky="ew")
        return workflow
