from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CONTENT_PAD, TEXT_MUTED


class ExportFilterDialogMixin1:
    def _ExportFilterDialog__init__p2(self, status_frame):
        ctk.CTkLabel(status_frame, text="Status:", font=ctk.CTkFont(size=11)).grid(
            row=1, column=0, padx=12, pady=4, sticky="w"
        )
        self.status_var = ctk.StringVar(value="")
        status_menu = ctk.CTkOptionMenu(
            status_frame,
            variable=self.status_var,
            values=["", "Active", "Inactive", "Pending", "Completed"],
            font=ctk.CTkFont(size=11),
        )
        status_menu.grid(row=1, column=1, padx=12, pady=4, sticky="ew")

        # ── Columns ─────────────────────────────────────────────────────
        columns_frame = ctk.CTkFrame(self, corner_radius=8)
        columns_frame.grid(row=3, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, 8))
        self.visible_only_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            columns_frame,
            text="Export visible columns only",
            variable=self.visible_only_var,
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=0, padx=12, pady=8, sticky="w")
        ctk.CTkLabel(
            columns_frame,
            text="Off = every sheet exports all columns (auditable). "
            "On = each sheet follows Columns (⋮) / hidden columns on matching tables.",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED,
            wraplength=360,
            justify="left",
        ).grid(row=1, column=0, padx=12, pady=(0, 8), sticky="w")

        # ── Buttons ─────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", padx=CONTENT_PAD, pady=(12, CONTENT_PAD))

        ctk.CTkButton(
            btn_frame,
            text="Export All (No Filters)",
            width=160,
            fg_color="transparent",
            border_width=1,
            command=self._export_all,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="Export with Filters",
            width=140,
            command=self._export_filtered,
        ).pack(side="right")
