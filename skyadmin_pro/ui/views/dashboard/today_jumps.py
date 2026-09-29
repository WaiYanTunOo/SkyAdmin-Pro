"""Relocated Open buttons — the boards live on their own menu pages."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import NAV_PIPELINE


def add_today_jumps(view, card) -> None:
    row = ctk.CTkFrame(card, fg_color="transparent")
    row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
    ctk.CTkButton(
        row,
        text="Open services",
        width=120,
        command=lambda: view.app.show_view(NAV_PIPELINE),
    ).pack(side="left")
