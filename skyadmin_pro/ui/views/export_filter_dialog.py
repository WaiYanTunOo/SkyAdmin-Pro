"""Export filter dialog — date range and status filters before Excel export."""

from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.ui.theme import CONTENT_PAD, TEXT_MUTED
from skyadmin_pro.ui.widgets import FeedbackLabel, make_modal, themed_entry


class ExportFilterDialog(ctk.CTkToplevel):
    """Modal dialog to set export filters before running export_to_excel."""

    def __init__(self, app: object, on_export) -> None:
        super().__init__(app)
        self.app = app
        self.on_export = on_export
        self.title("Export Filters")
        self.geometry("420x520")
        self.resizable(False, False)
        self.transient(app)
        make_modal(self)

        self.grid_columnconfigure(0, weight=1)

        # ── Title ─────────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Export to Excel",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=CONTENT_PAD, pady=(CONTENT_PAD, 12), sticky="w")

        # ── Date range ────────────────────────────────────────────────
        date_frame = ctk.CTkFrame(self, corner_radius=8)
        date_frame.grid(row=1, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, 8))
        date_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(date_frame, text="Date Range", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(8, 4), sticky="w"
        )

        ctk.CTkLabel(date_frame, text="From:", font=ctk.CTkFont(size=11)).grid(
            row=1, column=0, padx=12, pady=4, sticky="w"
        )
        self.date_from_var = ctk.StringVar(value="")
        themed_entry(date_frame, textvariable=self.date_from_var, placeholder_text="YYYY-MM-DD (optional)").grid(
            row=1, column=1, padx=12, pady=4, sticky="ew"
        )

        ctk.CTkLabel(date_frame, text="To:", font=ctk.CTkFont(size=11)).grid(
            row=2, column=0, padx=12, pady=4, sticky="w"
        )
        self.date_to_var = ctk.StringVar(value="")
        themed_entry(date_frame, textvariable=self.date_to_var, placeholder_text="YYYY-MM-DD (optional)").grid(
            row=2, column=1, padx=12, pady=4, sticky="ew"
        )

        # ── Status filter ─────────────────────────────────────────────
        status_frame = ctk.CTkFrame(self, corner_radius=8)
        status_frame.grid(row=2, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, 8))
        status_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(status_frame, text="Status Filter", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(8, 4), sticky="w"
        )

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
            columns_frame, text="Export visible columns only",
            variable=self.visible_only_var,
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=0, padx=12, pady=8, sticky="w")
        ctk.CTkLabel(
            columns_frame,
            text="Off = every sheet exports all columns (auditable). "
            "On = sheets follow hidden columns in Database & Tasks tables.",
            font=ctk.CTkFont(size=10), text_color=TEXT_MUTED,
            wraplength=360, justify="left",
        ).grid(row=1, column=0, padx=12, pady=(0, 8), sticky="w")

        # ── Buttons ─────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", padx=CONTENT_PAD, pady=(12, CONTENT_PAD))

        ctk.CTkButton(
            btn_frame, text="Export All (No Filters)", width=160,
            fg_color="transparent", border_width=1,
            command=self._export_all,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="Export with Filters", width=140,
            command=self._export_filtered,
        ).pack(side="right")

        self.feedback = FeedbackLabel(self)
        self.feedback.grid(row=5, column=0, sticky="ew", padx=CONTENT_PAD, pady=(0, 8))

    def _validate_date(self, value: str) -> str | None:
        if not value.strip():
            return None
        try:
            date.fromisoformat(value.strip())
            return value.strip()
        except ValueError:
            return None

    def _export_all(self) -> None:
        self.on_export(date_from=None, date_to=None, status=None, visible_only=self.visible_only_var.get())
        self.destroy()

    def _export_filtered(self) -> None:
        d_from = self._validate_date(self.date_from_var.get())
        d_to = self._validate_date(self.date_to_var.get())
        status = self.status_var.get().strip() or None

        if self.date_from_var.get().strip() and d_from is None:
            self.feedback.error("Invalid 'from' date format. Use YYYY-MM-DD.")
            return
        if self.date_to_var.get().strip() and d_to is None:
            self.feedback.error("Invalid 'to' date format. Use YYYY-MM-DD.")
            return

        self.on_export(date_from=d_from, date_to=d_to, status=status, visible_only=self.visible_only_var.get())
        self.destroy()
