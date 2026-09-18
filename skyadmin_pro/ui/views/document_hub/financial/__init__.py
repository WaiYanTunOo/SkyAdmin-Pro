"""Document Hub — financial documents panel."""

from __future__ import annotations

import customtkinter as ctk

from .financialDocsPanelMixin0 import FinancialDocsPanelMixin0
from .financialDocsPanelMixin1 import FinancialDocsPanelMixin1


class FinancialDocsPanel(FinancialDocsPanelMixin0, FinancialDocsPanelMixin1, ctk.CTkFrame):
    pass
