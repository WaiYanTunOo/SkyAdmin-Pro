"""Renewals tab — per-client service checklist and countdown."""

from __future__ import annotations

import customtkinter as ctk

from .renewalPanelMixin0 import RenewalPanelMixin0
from .renewalPanelMixin1 import RenewalPanelMixin1
from .renewalPanelMixin2 import RenewalPanelMixin2
from .renewalPanelMixin3 import RenewalPanelMixin3


class RenewalPanel(RenewalPanelMixin0, RenewalPanelMixin1, RenewalPanelMixin2, RenewalPanelMixin3, ctk.CTkFrame):
    pass
