from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.widgets import FeedbackLabel, themed_tabview

from ._const_8 import TAB_NAMES


class DatabaseTasksViewMixin0:
    title = "Companies"
    subtitle = "Company details and services. Not the daily work queue."

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)

        self._lazy_panels: dict[str, object] = {}

        toolbar = ctk.CTkFrame(self.body, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            toolbar,
            text="Export to Excel",
            width=140,
            command=self._export_excel,
        ).grid(row=0, column=0, sticky="w")
        self.feedback = FeedbackLabel(toolbar)
        self.feedback.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        self.tabs = themed_tabview(self.body, command=self._on_tab_changed)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        for name in TAB_NAMES:
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self.tasks_panel = None
        self.clients_panel = None
        self.courier_panel = None
        self.month_panel = None
        self.renewals_panel = None
        self.pipeline_panel = None
        self.company_panel = None
        self.accounting_setup_panel = None
        self.suppliers_panel = None
