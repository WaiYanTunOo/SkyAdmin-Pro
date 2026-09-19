"""Empty-state overlay for ThemedTreeview."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED


def ensure_empty_overlay(host: ctk.CTkFrame) -> ctk.CTkLabel:
    """Create (once) a centered empty-message label over the tree area."""
    label = getattr(host, "_empty_overlay", None)
    if label is not None:
        try:
            if label.winfo_exists():
                return label
        except tk.TclError:
            pass
    label = ctk.CTkLabel(
        host,
        text="",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=13),
        justify="center",
        wraplength=420,
    )
    host._empty_overlay = label
    return label


def show_empty_overlay(host: ctk.CTkFrame, message: str) -> None:
    label = ensure_empty_overlay(host)
    label.configure(text=message)
    label.place(relx=0.5, rely=0.5, anchor="center")
    try:
        label.lift()
    except tk.TclError:
        pass


def hide_empty_overlay(host: ctk.CTkFrame) -> None:
    label = getattr(host, "_empty_overlay", None)
    if label is None:
        return
    try:
        label.place_forget()
    except tk.TclError:
        pass
