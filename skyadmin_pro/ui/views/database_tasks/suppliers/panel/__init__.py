"""Suppliers & AP tab shell — composes directory, services, and payments sub-tabs."""

from __future__ import annotations

import customtkinter as ctk

from .suppliersPanelMixin0 import SuppliersPanelMixin0
from .suppliersPanelMixin1 import SuppliersPanelMixin1


class SuppliersPanel(SuppliersPanelMixin0, SuppliersPanelMixin1, ctk.CTkFrame):
    pass
