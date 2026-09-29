"""Header / history / input builders for SkyAgent chat."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from skyadmin_pro.ui.theme import CONTENT_PAD, TEXT_MUTED
from skyadmin_pro.ui.widgets import themed_entry, themed_scrollable_frame

from ._msg_helpers import add_bubble


def build_header(panel: Any) -> ctk.CTkLabel:
    header = ctk.CTkFrame(panel, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=CONTENT_PAD, pady=(CONTENT_PAD, 4))
    header.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(header, text="SkyAgent", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
    status = ctk.CTkLabel(header, text="Ready (offline)", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
    status.grid(row=0, column=1, sticky="e")
    return status


def build_history(panel: Any) -> Any:
    history = themed_scrollable_frame(panel)
    history.grid(row=1, column=0, sticky="nsew", padx=CONTENT_PAD, pady=(0, 4))
    history.grid_columnconfigure(0, weight=1)
    add_bubble(
        history,
        "Hello! I'm SkyAgent. Ask about clients, tasks, documents, or policies.",
        is_user=False,
    )
    return history


def build_input(panel: Any, input_var: Any, on_send: Callable[[], None]) -> None:
    frame = ctk.CTkFrame(panel, fg_color="transparent")
    frame.grid(row=2, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, CONTENT_PAD))
    frame.grid_columnconfigure(0, weight=1)
    entry = themed_entry(frame, textvariable=input_var, placeholder_text="Type your message\u2026")
    entry.grid(row=0, column=0, sticky="ew")
    entry.bind("<Return>", lambda _: on_send())
    ctk.CTkButton(frame, text="Send", width=60, command=on_send).grid(row=0, column=1, padx=(8, 0))
