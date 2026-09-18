"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import TEXT_MUTED

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).
from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_NAMES,
)
from skyadmin_pro.ui.widgets import (
    FeedbackLabel,
    themed_tabview,
)


class CompanyDetailsPanelMixin1:
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._editing_service_id: int | None = None
        self._editing_doc_id: int | None = None
        self._filing_suspend_save = False
        self._lazy_tabs: set[str] = set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        selector = ctk.CTkFrame(self, fg_color="transparent")
        selector.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        selector.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(selector, text="Company / Client:", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 10))
        from skyadmin_pro.ui.widgets import bind_wrap_label, combo_style_kwargs

        self.company_box = ctk.CTkComboBox(
            selector,
            values=[""],
            command=self._on_company,
            **combo_style_kwargs(),
        )
        self.company_box.grid(row=0, column=1, sticky="ew")

        actions = ctk.CTkFrame(selector, fg_color="transparent")
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        actions.grid_columnconfigure(0, weight=1)
        self.company_info = ctk.CTkLabel(actions, text="", text_color=TEXT_MUTED, anchor="w", justify="left")
        self.company_info.grid(row=0, column=0, sticky="ew")
        bind_wrap_label(self.company_info, actions, pad=200)
        ctk.CTkButton(
            actions,
            text="Missing docs workflow",
            width=180,
            command=self._missing_docs_workflow,
        ).grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.tabs = themed_tabview(self, command=self._on_subtab_changed)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        for name in SUBTAB_NAMES:
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
