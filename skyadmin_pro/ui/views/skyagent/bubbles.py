"""Chat bubble widget for SkyAgent conversation display."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, TEXT_MUTED


class ChatBubble(ctk.CTkFrame):
    """A single message bubble (user or agent)."""

    def __init__(
        self,
        master,
        *,
        text: str,
        is_user: bool = True,
        timestamp: str = "",
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=CARD_RADIUS, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self._is_user = is_user
        self._build_content(text, timestamp)

    def _build_content(self, text: str, timestamp: str) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 2))

        role = "You" if self._is_user else "SkyAgent"
        ctk.CTkLabel(
            header,
            text=role,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).pack(side="left")

        if timestamp:
            ctk.CTkLabel(
                header,
                text=timestamp,
                font=ctk.CTkFont(size=10),
                text_color=TEXT_MUTED,
                anchor="e",
            ).pack(side="right")

        body = ctk.CTkLabel(
            self,
            text=text,
            anchor="w",
            justify="left",
            wraplength=380,
        )
        body.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        body.bind("<Configure>", lambda e: e.widget.configure(wraplength=max(240, e.width - 24)))

    @property
    def is_user(self) -> bool:
        return self._is_user
