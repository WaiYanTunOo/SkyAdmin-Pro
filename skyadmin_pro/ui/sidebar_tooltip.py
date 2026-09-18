"""Lightweight tooltip for collapsed sidebar buttons."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk


class SidebarTooltip:
    """Shows a small popup to the right of a collapsed sidebar button."""

    def __init__(self, widget: ctk.CTkButton, text: str) -> None:
        self._widget = widget
        self._text = text
        self._top: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self._top is not None:
            return
        try:
            x = self._widget.winfo_rootx() + self._widget.winfo_width() + 8
            y = self._widget.winfo_rooty() + self._widget.winfo_height() // 2 - 12
            top = tk.Toplevel(self._widget)
            top.wm_overrideredirect(True)
            top.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                top,
                text=self._text,
                background="#1e1e1e" if ctk.get_appearance_mode() == "Dark" else "#f4f4f5",
                foreground="#f4f4f5" if ctk.get_appearance_mode() == "Dark" else "#1e1e1e",
                padx=8,
                pady=4,
                font=("Segoe UI", 11),
            )
            label.pack()
            self._top = top
        except Exception:
            self._top = None

    def _hide(self, _event=None) -> None:
        if self._top is not None:
            try:
                self._top.destroy()
            except Exception:
                pass
            self._top = None
