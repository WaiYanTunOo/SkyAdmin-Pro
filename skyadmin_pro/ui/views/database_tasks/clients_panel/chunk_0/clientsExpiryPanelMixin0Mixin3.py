from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED


class ClientsExpiryPanelMixin0Mixin3:
    def _ClientsExpiryPanelMixin0__init__p4(self, actions, left):
        ctk.CTkButton(
            actions,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._delete_client,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Open Suppliers",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._open_suppliers,
        ).pack(side="left", padx=(8, 0))

        # Batch action row — Ctrl/Shift+click multi-select (selectmode extended)
        batch_row = ctk.CTkFrame(left, fg_color="transparent")
        batch_row.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 8))
        ctk.CTkLabel(
            batch_row,
            text="Batch:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(0, 6))
        self._batch_selection_label = ctk.CTkLabel(
            batch_row,
            text="0 selected",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_MUTED,
        )
        self._batch_selection_label.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            batch_row,
            text="Archive selected",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._batch_archive,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row,
            text="Delete selected",
            width=110,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._batch_delete,
        ).pack(side="left", padx=(0, 4))
        return batch_row
