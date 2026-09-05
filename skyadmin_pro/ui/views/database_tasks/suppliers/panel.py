"""Suppliers & AP tab shell — composes directory, services, and payments sub-tabs."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.views.database_tasks.suppliers.directory_tab import SupplierDirectoryTab
from skyadmin_pro.ui.views.database_tasks.suppliers.payments_tab import SupplierPaymentsTab
from skyadmin_pro.ui.views.database_tasks.suppliers.services_tab import SupplierServicesTab
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_tabview


class SuppliersPanel(ctk.CTkFrame):
    """Supplier directory + supplier services + pending supplier payments (AP)."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tabs = themed_tabview(self, command=self._on_supplier_tab_changed)
        tabs.grid(row=0, column=0, sticky="nsew")
        self._supplier_tabs = tabs
        self._lazy_supplier_tabs: set[str] = set()
        for name in ("Suppliers", "Supplier Services", "Payments (AP)"):
            tabs.add(name)
            tab = tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self.directory: SupplierDirectoryTab | None = None
        self.services: SupplierServicesTab | None = None
        self.payments: SupplierPaymentsTab | None = None
        # Backward compatibility placeholders
        self.supplier_tree = None
        self.supplier_svc_tree = None
        self.pay_tree = None
        self.pay_supplier = None
        # Build default tab eagerly (Suppliers)
        self._ensure_supplier_tab("Suppliers")
        if self.directory:
            self.directory.on_supplier_selected = lambda _sid: self.services.refresh() if self.services else None

    def _ensure_supplier_tab(self, name: str) -> None:
        if not hasattr(self, "_lazy_supplier_tabs"):
            self._lazy_supplier_tabs = set()  # type: ignore[attr-defined]
        if name in self._lazy_supplier_tabs:
            return
        # If panel already injected (unit test via __new__), treat as built
        if name == "Suppliers" and getattr(self, "directory", None) is not None:
            self._lazy_supplier_tabs.add(name)
            return
        if name == "Supplier Services" and getattr(self, "services", None) is not None:
            self._lazy_supplier_tabs.add(name)
            return
        if name == "Payments (AP)" and getattr(self, "payments", None) is not None:
            self._lazy_supplier_tabs.add(name)
            return
        if name == "Suppliers":
            self.directory = SupplierDirectoryTab(self._supplier_tabs.tab("Suppliers"), self)
            self._lazy_supplier_tabs.add(name)
            self.supplier_tree = self.directory.supplier_tree
            self.directory.on_supplier_selected = lambda _sid: (
                self.services.refresh() if self.services and "Supplier Services" in self._lazy_supplier_tabs else None
            )
        elif name == "Supplier Services":
            self.services = SupplierServicesTab(self._supplier_tabs.tab("Supplier Services"), self)
            self._lazy_supplier_tabs.add(name)
            self.supplier_svc_tree = self.services.supplier_svc_tree
        elif name == "Payments (AP)":
            self.payments = SupplierPaymentsTab(self._supplier_tabs.tab("Payments (AP)"), self)
            self._lazy_supplier_tabs.add(name)
            self.pay_tree = self.payments.pay_tree
            self.pay_supplier = self.payments.pay_supplier

    def _on_supplier_tab_changed(self) -> None:
        try:
            cur = self._supplier_tabs.get()
        except Exception:
            cur = "Suppliers"
        self._ensure_supplier_tab(cur)
        self.refresh_active_tab(cur)

    def refresh(self) -> None:
        """Reload the active Suppliers sub-tab only."""
        try:
            cur = self._supplier_tabs.get()
        except Exception:
            cur = "Suppliers"
        self._ensure_supplier_tab(cur)
        self.refresh_active_tab(cur)

    def refresh_active_tab(self, tab_name: str | None = None) -> None:
        if tab_name is None:
            try:
                tab_name = self._supplier_tabs.get()
            except Exception:
                tab_name = "Suppliers"
        self._ensure_supplier_tab(tab_name)
        if tab_name == "Suppliers" and self.directory:
            self.directory.refresh()
        elif tab_name == "Supplier Services" and self.services:
            self.services.refresh()
        elif tab_name == "Payments (AP)" and self.payments:
            self.payments.refresh()

    def refresh_after_directory_change(self) -> None:
        """Refresh directory data and any dependent sub-tab combos."""
        if self.directory:
            self.directory.refresh()
        if self.services:
            self.services.refresh()
        if self.payments:
            self.payments.refresh()
