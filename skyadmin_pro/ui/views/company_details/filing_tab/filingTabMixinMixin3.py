from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import FILING_FIELD_GROUPS, TAX_FILING_LABELS, TAX_FILING_STATUSES
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import TEXT_MUTED


class FilingTabMixinMixin3:
    def _FilingTabMixin_build_filing_statuses_fo_p2(self, frame):
        self._filing_save_schedulers: dict[str, object] = {}
        row = 2
        for group_title, fields in FILING_FIELD_GROUPS:
            ctk.CTkLabel(
                frame,
                text=group_title,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=TEXT_MUTED,
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 2))
            row += 1
            for field in fields:
                ctk.CTkLabel(frame, text=TAX_FILING_LABELS[field], font=ctk.CTkFont(size=13)).grid(
                    row=row, column=0, sticky="w", padx=16, pady=(4, 2)
                )
                var = ctk.StringVar(value="Not Applicable")
                self.filing_vars[field] = var

                def _schedule_save(f: str = field) -> None:
                    if self._filing_suspend_save:
                        return
                    self._persist_filing_field(f)

                self._filing_save_schedulers[field] = debounced_after(self, _schedule_save, delay_ms=300)
                var.trace_add("write", lambda *_a, f=field: self._filing_save_schedulers[f]())
                ctk.CTkOptionMenu(frame, values=list(TAX_FILING_STATUSES), variable=var).grid(
                    row=row, column=1, sticky="ew", padx=(0, 16), pady=(4, 2)
                )
                row += 1
        self._filing_form_next_row = row

    def _FilingTabMixin_build_filing_statuses_fo_p3(self, frame):
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(
            row=getattr(self, "_filing_form_next_row", 20),
            column=0,
            columnspan=2,
            sticky="w",
            padx=16,
            pady=(12, 8),
        )
        ctk.CTkLabel(
            btn_row,
            text="Changes save automatically when you pick a status.",
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            btn_row,
            text="Reset All to N/A",
            width=140,
            fg_color=("#dc2626", "#b91c1c"),
            hover_color=("#b91c1c", "#991b1b"),
            command=self._reset_all_filing_statuses,
        ).pack(side="left")
