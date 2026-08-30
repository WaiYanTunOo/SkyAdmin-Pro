"""Database & Tasks: live task table, courier tracker, clients, and Excel export."""

from __future__ import annotations

from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.services.export import default_export_name, export_to_excel
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.views.company_details import CompanyDetailsPanel
from skyadmin_pro.ui.widgets import FeedbackLabel, MonthStatusPanel

from skyadmin_pro.ui.views.database_tasks.clients_panel import ClientsExpiryPanel
from skyadmin_pro.ui.views.database_tasks.courier_panel import CourierPanel
from skyadmin_pro.ui.views.database_tasks.pipeline_panel import ServicePipelinePanel
from skyadmin_pro.ui.views.database_tasks.renewal_panel import RenewalPanel
from skyadmin_pro.ui.views.database_tasks.suppliers_panel import SuppliersPanel
from skyadmin_pro.ui.views.database_tasks.task_panel import TaskPanel


class DatabaseTasksView(BaseView):
    title = "Database & Tasks"
    subtitle = "Offline SQLite tracking for clients, tasks, courier deliveries, and expiry dates."

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)

        self._lazy_panels: dict[str, object] = {}

        toolbar = ctk.CTkFrame(self.body, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            toolbar,
            text="Export to Excel",
            width=140,
            command=self._export_excel,
        ).grid(row=0, column=0, sticky="w")
        self.feedback = FeedbackLabel(toolbar)
        self.feedback.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        self.tabs = ctk.CTkTabview(self.body, command=self._on_tab_changed)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        for name in (
            "Tasks",
            "Courier Tracker",
            "Clients & Expiry",
            "Monthly Tax Status",
            "Company Details",
            "Renewals",
            "Service Pipeline",
            "Suppliers & AP",
        ):
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_propagate(False)

        self.tasks_panel = TaskPanel(self.tabs.tab("Tasks"), self.app, self.feedback)
        self.tasks_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._lazy_panels["Tasks"] = self.tasks_panel

        self.clients_panel = ClientsExpiryPanel(self.tabs.tab("Clients & Expiry"), self.app, self.feedback)
        self.clients_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._lazy_panels["Clients & Expiry"] = self.clients_panel

        self.courier_panel = None
        self.month_panel = None
        self.renewals_panel = None
        self.pipeline_panel = None
        self.company_panel = None
        self.suppliers_panel = None

    def _ensure_lazy_panel(self, name: str) -> None:
        if name in self._lazy_panels:
            return
        if name == "Courier Tracker":
            self.courier_panel = CourierPanel(self.tabs.tab("Courier Tracker"), self.app, self.feedback)
            self.courier_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.courier_panel
        elif name == "Monthly Tax Status":
            month_scroll = ctk.CTkScrollableFrame(self.tabs.tab("Monthly Tax Status"), fg_color="transparent")
            month_scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            month_scroll.grid_columnconfigure(0, weight=1)
            self.month_panel = MonthStatusPanel(
                month_scroll,
                self.app,
                showheight=12,
                title="Monthly tax status per client",
            )
            self.month_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.month_panel
        elif name == "Company Details":
            self.company_panel = CompanyDetailsPanel(self.tabs.tab("Company Details"), self.app, self.feedback)
            self.company_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.company_panel
        elif name == "Renewals":
            self.renewals_panel = RenewalPanel(self.tabs.tab("Renewals"), self.app, self.feedback)
            self.renewals_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.renewals_panel
        elif name == "Service Pipeline":
            self.pipeline_panel = ServicePipelinePanel(self.tabs.tab("Service Pipeline"), self.app, self.feedback)
            self.pipeline_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.pipeline_panel
        elif name == "Suppliers & AP":
            self.suppliers_panel = SuppliersPanel(self.tabs.tab("Suppliers & AP"), self.app, self.feedback)
            self.suppliers_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.suppliers_panel

    def _on_tab_changed(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = ""
        self._ensure_lazy_panel(current)
        self._refresh_active_tab(current)

    def _refresh_active_tab(self, tab_name: str) -> None:
        self._refresh_service_menus()
        if tab_name == "Tasks":
            self.tasks_panel.refresh()
        elif tab_name == "Courier Tracker" and self.courier_panel is not None:
            self.courier_panel.refresh()
        elif tab_name == "Clients & Expiry":
            self.clients_panel.refresh()
        elif tab_name == "Monthly Tax Status" and self.month_panel is not None:
            self.month_panel.refresh()
        elif tab_name == "Company Details" and self.company_panel is not None:
            self.company_panel.refresh()
        elif tab_name == "Renewals" and self.renewals_panel is not None:
            self.renewals_panel.refresh()
        elif tab_name == "Service Pipeline" and self.pipeline_panel is not None:
            self.pipeline_panel.refresh()
        elif tab_name == "Suppliers & AP" and self.suppliers_panel is not None:
            self.suppliers_panel.refresh()

    def _require_company_panel(self) -> CompanyDetailsPanel:
        self._ensure_lazy_panel("Company Details")
        assert self.company_panel is not None
        return self.company_panel

    def on_show(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = "Tasks"
        self._ensure_lazy_panel(current)
        self._refresh_active_tab(current)

    def open_company_details(self, client_name: str) -> None:
        self.tabs.set("Company Details")
        panel = self._require_company_panel()
        panel.select_client(client_name)
        panel.refresh()

    def open_company_tax_ids(self, client_name: str) -> None:
        self.tabs.set("Company Details")
        panel = self._require_company_panel()
        panel.select_client(client_name)
        panel.tabs.set("Tax IDs")
        panel.refresh()

    def open_accounting_setup(self) -> None:
        self.tabs.set("Company Details")
        panel = self._require_company_panel()
        panel.tabs.set("Accounting Setup")
        panel.refresh_accounting_setup()

    def open_vo_csh_setup(self) -> None:
        self.tabs.set("Company Details")
        panel = self._require_company_panel()
        panel.tabs.set("VO/CSH Setup")
        panel.refresh_vo_csh_setup()

    def open_company_vo_csh(self, client_name: str) -> None:
        self.tabs.set("Company Details")
        panel = self._require_company_panel()
        panel.select_client(client_name)
        panel.tabs.set("VO & CSH")
        panel.refresh()

    def open_task(self, task_id: int) -> None:
        self.tabs.set("Tasks")
        self.tasks_panel.select_task(task_id)

    def open_renewal(self, client_name: str) -> None:
        self._ensure_lazy_panel("Renewals")
        self.tabs.set("Renewals")
        assert self.renewals_panel is not None
        self.renewals_panel.select_client(client_name)
        self.renewals_panel.refresh()

    def open_pipeline(self) -> None:
        self._ensure_lazy_panel("Service Pipeline")
        self.tabs.set("Service Pipeline")
        if self.pipeline_panel is not None:
            self.pipeline_panel.refresh()

    def refresh_all(self) -> None:
        if not hasattr(self, "tasks_panel"):
            return
        try:
            current = self.tabs.get()
        except Exception:
            current = "Tasks"
        self._ensure_lazy_panel(current)
        self._refresh_active_tab(current)

    def _refresh_service_menus(self) -> None:
        types = self.app.db.list_service_types()
        if hasattr(self, "clients_panel") and self.clients_panel is not None:
            combo = self.clients_panel.expiry_type
            combo.configure(values=types)
            if combo.get() not in types:
                combo.set(types[0])
        if self.company_panel is not None:
            combo = self.company_panel.service_type
            combo.configure(values=types)
            if combo.get() not in types:
                combo.set(types[0])
        if self.pipeline_panel is not None:
            combo = self.pipeline_panel.pipe_service
            combo.configure(values=types)
            if combo.get() not in types:
                combo.set(types[0])

    def _export_excel(self) -> None:
        target = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Export database to Excel",
            defaultextension=".xlsx",
            initialfile=default_export_name(),
            initialdir=str(self.app.paths.root),
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if not target:
            return
        try:
            path = export_to_excel(self.app.db, target)
        except Exception as exc:
            self.feedback.error(f"Export failed: {exc}")
            messagebox.showerror("Export failed", str(exc), parent=self.winfo_toplevel())
            return
        self.feedback.success(f"Exported to {path.name}")
        self.app.set_status(f"Exported database to {path}")
