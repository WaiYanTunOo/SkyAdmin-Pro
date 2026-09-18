from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED


class DashboardViewMixin14:
    def _DashboardView_build_detail_trees_heavy_p2(self, report_card):
        self.report_tree.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.report_hint = ctk.CTkLabel(
            report_card,
            text="Document rows edit the company file. Pipeline amount is from fee matrix.",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.report_hint.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))
        return report_card

    def _DashboardView_build_detail_trees_heavy_p3(self, tax_overview):
        self._detail_stage = 3
        self._detail_built = True
        if getattr(self, "_last_snap", None) is not None:
            self._refresh_report()
        self._detail_scroll._on_content_configure()
