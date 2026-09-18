from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.widgets import FeedbackLabel


class DashboardViewMixin9:
    def _DashboardView_build_header_extras_p2(self, workflow):
        ctk.CTkButton(
            workflow,
            text="Generate Workspace",
            width=170,
            command=self._generate_workspace,
        ).grid(row=0, column=2, padx=(0, 16), pady=14, sticky="w")

        folders = ctk.CTkFrame(workflow, fg_color="transparent")
        folders.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16)
        folders.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            folders,
            text="Open Workspace",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._open_folder(self.app.paths.root),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            folders,
            text="Open Clients",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._open_folder(self.app.paths.clients),
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkButton(
            folders,
            text="Open Suppliers",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._open_folder(self.app.paths.suppliers),
        ).grid(row=0, column=2, sticky="w", padx=(8, 0))
        ctk.CTkButton(
            folders,
            text="Export PDF",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._export_pdf,
        ).grid(row=0, column=3, sticky="w", padx=(8, 0))

        self.workflow_feedback = FeedbackLabel(workflow)
        self.workflow_feedback.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))

        next_card = ctk.CTkFrame(self._today, corner_radius=12)
        next_card.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        next_card.grid_columnconfigure(0, weight=1)
        return next_card

    def _DashboardView_build_header_extras_p3(self, next_card):
        from .today_jumps import add_today_jumps

        add_today_jumps(self, next_card)
        self._detail_scroll._on_content_configure()
