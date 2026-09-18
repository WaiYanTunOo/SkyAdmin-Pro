"""Accounting Setup as a Companies (Database & Tasks) main tab."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.widgets import FeedbackLabel

from .mixin0 import AccountingSetupPanelMixin0
from .mixin1 import AccountingSetupPanelMixin1


class AccountingSetupPanel(AccountingSetupPanelMixin0, AccountingSetupPanelMixin1, ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        frame = self._build_accounting_setup(self)
        frame.grid(row=0, column=0, sticky="nsew")
