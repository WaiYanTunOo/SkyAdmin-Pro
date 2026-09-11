"""Shared view chrome: page header + placeholder body."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CONTENT_PAD, HEADER_SUBTITLE_SIZE, HEADER_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.widgets import bind_wrap_label


class BaseView(ctk.CTkFrame):
    """Every sidebar destination is a BaseView hosted in the content area."""

    title = "View"
    subtitle = ""

    def __init__(self, master: ctk.CTkFrame, app: object, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=CONTENT_PAD, pady=(0, CONTENT_PAD))
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)
        self.build()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=CONTENT_PAD, pady=(CONTENT_PAD, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=self.title,
            font=ctk.CTkFont(size=HEADER_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        if self.subtitle:
            self._subtitle_label = ctk.CTkLabel(
                header,
                text=self.subtitle,
                font=ctk.CTkFont(size=HEADER_SUBTITLE_SIZE),
                text_color=TEXT_MUTED,
                anchor="w",
                justify="left",
            )
            self._subtitle_label.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            bind_wrap_label(self._subtitle_label, header, pad=8)

    def build(self) -> None:
        """Override in subclasses to populate self.body."""

    def on_show(self) -> None:
        """Called each time the sidebar switches to this view."""

    def on_hide(self) -> None:
        """Called when the sidebar leaves this view."""
