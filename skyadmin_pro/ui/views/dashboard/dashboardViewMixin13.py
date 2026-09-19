from __future__ import annotations

from datetime import date

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview

from .report_rows import edit_selected, open_report_row


class DashboardViewMixin13:
    def _DashboardView_build_detail_trees_heavy_p1(self):
        if getattr(self, "_detail_stage", 0) < 2:
            self._build_detail_trees_secondary()

        report_card = ctk.CTkFrame(self._incentive, corner_radius=12)
        report_card.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        report_card.grid_columnconfigure(0, weight=1)
        report_card.grid_rowconfigure(1, weight=1)
        report_header = ctk.CTkFrame(report_card, fg_color="transparent")
        report_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        report_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            report_header,
            text="Monthly incentive report — Fees and new pipeline this month",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        now = date.today()
        self._report_months = []
        for i in range(12):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            self._report_months.append((y, m))
        month_labels = [f"{date(y, m, 1):%b %Y}" for y, m in self._report_months]
        self._report_month_var = ctk.StringVar(value=month_labels[0])
        ctk.CTkOptionMenu(
            report_header,
            variable=self._report_month_var,
            values=month_labels,
            width=140,
            command=lambda _: self._refresh_report(),
        ).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(report_header, text="Edit", width=70, command=lambda: edit_selected(self)).grid(
            row=0, column=2, padx=(8, 0)
        )
        ctk.CTkButton(report_header, text="Export Excel", width=110, command=self._export_report).grid(
            row=0, column=3, padx=(8, 0)
        )
        self._report_rows = {}
        self.report_tree = ThemedTreeview(
            report_card,
            columns=(
                ("no", "No.", 50),
                ("date", "Date", 110),
                ("client", "Client", 180),
                ("source", "Source", 100),
                ("service", "Service", 200),
                ("amount", "Amount", 110),
            ),
            on_double_click=lambda iid: open_report_row(self, iid),
            showheight=8,
            table_id="dashboard.incentive_report",
            db=self.app.db,
        )
        return report_card
