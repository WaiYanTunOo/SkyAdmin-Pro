"""Suppliers & AP tab shell — composes directory, services, and payments sub-tabs."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.widgets import FeedbackLabel, themed_tabview

from skyadmin_pro.ui.views.database_tasks.suppliers.directory_tab import SupplierDirectoryTab
from skyadmin_pro.ui.views.database_tasks.suppliers.payments_tab import SupplierPaymentsTab
from skyadmin_pro.ui.views.database_tasks.suppliers.services_tab import SupplierServicesTab


class SuppliersPanel(ctk.CTkFrame):
    """Supplier directory + supplier services + pending supplier payments (AP)."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tabs = themed_tabview(self)
        tabs.grid(row=0, column=0, sticky="nsew")
        for name in ("Suppliers", "Supplier Services", "Payments (AP)"):
            tabs.add(name)
            tab = tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_propagate(False)

        self.directory = SupplierDirectoryTab(tabs.tab("Suppliers"), self)
        self.services = SupplierServicesTab(tabs.tab("Supplier Services"), self)
        self.payments = SupplierPaymentsTab(tabs.tab("Payments (AP)"), self)

        self.directory.on_supplier_selected = lambda _sid: self.services.refresh()

        # Backward compatibility for any code that accessed these widgets directly.
        self.supplier_tree = self.directory.supplier_tree
        self.supplier_svc_tree = self.services.supplier_svc_tree
        self.pay_tree = self.payments.pay_tree
        self.pay_supplier = self.payments.pay_supplier

    def refresh(self) -> None:
        suppliers = self.directory.refresh()
        self.services.refresh()
        self.payments.refresh(suppliers)
