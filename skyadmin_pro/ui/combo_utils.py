"""Small helpers for combo boxes."""

from __future__ import annotations

import customtkinter as ctk


def fill_combo(combo: ctk.CTkComboBox, values: list[str], current: str = "") -> None:
    combo.configure(values=values or [""])
    combo.set(current)
