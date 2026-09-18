"""Courier tracker tab — outgoing delivery log."""

from __future__ import annotations

import customtkinter as ctk

from ._const_0 import FORM_PADX
from .courierPanelMixin0 import CourierPanelMixin0
from .courierPanelMixin1 import CourierPanelMixin1
from .courierPanelMixin2 import CourierPanelMixin2
from .courierPanelMixin3 import CourierPanelMixin3
from .courierPanelMixin4 import CourierPanelMixin4


class CourierPanel(
    CourierPanelMixin0, CourierPanelMixin1, CourierPanelMixin2, CourierPanelMixin3, CourierPanelMixin4, ctk.CTkFrame
):
    pass
