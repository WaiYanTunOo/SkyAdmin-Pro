"""Document Hub — Smart Renamer panel."""

from __future__ import annotations

import customtkinter as ctk

from .smartRenamerPanelMixin0 import SmartRenamerPanelMixin0
from .smartRenamerPanelMixin1 import SmartRenamerPanelMixin1
from .smartRenamerPanelMixin2 import SmartRenamerPanelMixin2
from .smartRenamerPanelMixin3 import SmartRenamerPanelMixin3
from .smartRenamerPanelMixin4 import SmartRenamerPanelMixin4


class SmartRenamerPanel(
    SmartRenamerPanelMixin0,
    SmartRenamerPanelMixin1,
    SmartRenamerPanelMixin2,
    SmartRenamerPanelMixin3,
    SmartRenamerPanelMixin4,
    ctk.CTkFrame,
):
    pass
