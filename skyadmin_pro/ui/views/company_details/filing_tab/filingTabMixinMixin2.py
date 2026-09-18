from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import (
    CARD_RADIUS,
    CARD_TITLE_SIZE,
    STATUS_COMPLETE,
    STATUS_ONGOING,
    STATUS_PENDING,
    TEXT_FAINT,
    TEXT_MUTED,
)


class FilingTabMixinMixin2:
    def _FilingTabMixin_build_filing_statuses_fo_p1(self, master):
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid(row=0, column=0, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        # Title row
        title_row = ctk.CTkFrame(frame, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            title_row,
            text="Statutory returns — not month close",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        self.filing_last_changed_label = ctk.CTkLabel(
            title_row,
            text="",
            text_color=TEXT_FAINT,
            font=ctk.CTkFont(size=11),
        )
        self.filing_last_changed_label.grid(row=0, column=1, sticky="e")

        # Progress summary bar
        summary_frame = ctk.CTkFrame(frame, fg_color="transparent")
        summary_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.filing_summary_labels: dict[str, ctk.CTkLabel] = {}
        for idx, (key, color) in enumerate(
            [
                ("complete", STATUS_COMPLETE),
                ("ongoing", STATUS_ONGOING),
                ("pending", STATUS_PENDING),
                ("na", TEXT_MUTED),
            ]
        ):
            lbl = ctk.CTkLabel(
                summary_frame,
                text="0",
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=color,
            )
            lbl.grid(row=0, column=idx, sticky="w", padx=(0 if idx == 0 else 16, 0))
            ctk.CTkLabel(
                summary_frame,
                text=["Complete", "On-Going", "Pending", "N/A"][idx],
                text_color=TEXT_MUTED,
                font=ctk.CTkFont(size=11),
            ).grid(row=1, column=idx, sticky="w", padx=(0 if idx == 0 else 16, 0))
            self.filing_summary_labels[key] = lbl

        # Filing status rows
        self.filing_vars: dict[str, ctk.StringVar] = {}
        self.filing_labels: dict[str, ctk.CTkLabel] = {}
        return frame
