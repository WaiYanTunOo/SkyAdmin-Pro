"""Database & Tasks: live task table, courier tracker, clients, and Excel export."""

from __future__ import annotations

from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.services.export import default_export_name, export_to_excel
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.views.company_details import CompanyDetailsPanel
from skyadmin_pro.ui.views.company_details.panel import (
    SUBTAB_ACCOUNTING,
    SUBTAB_TAX_IDS,
    SUBTAB_VO_CSH,
    SUBTAB_VO_CSH_SETUP,
)
from skyadmin_pro.ui.views.database_tasks.clients_panel import ClientsExpiryPanel
from skyadmin_pro.ui.views.database_tasks.courier_panel import CourierPanel
from skyadmin_pro.ui.views.database_tasks.pipeline_panel import ServicePipelinePanel
from skyadmin_pro.ui.views.database_tasks.renewal_panel import RenewalPanel
from skyadmin_pro.ui.views.database_tasks.suppliers_panel import SuppliersPanel
from skyadmin_pro.ui.views.database_tasks.task_panel import TaskPanel
from skyadmin_pro.ui.widgets import FeedbackLabel, MonthStatusPanel, themed_tabview

# Tab names — single source of truth; the tabview, lazy loader, refresh
# dispatcher, and service-menu map must all use these, never raw strings.
TAB_TASKS = "Tasks"
TAB_COURIER = "Courier Tracker"
TAB_CLIENTS = "Clients & Expiry"
TAB_MONTH = "Monthly Tax Status"
TAB_COMPANY = "Company Details"
TAB_RENEWALS = "Renewals"
TAB_PIPELINE = "Service Pipeline"
TAB_SUPPLIERS = "Suppliers & AP"

TAB_NAMES: tuple[str, ...] = (
    TAB_TASKS,
    TAB_COURIER,
    TAB_CLIENTS,
    TAB_MONTH,
    TAB_COMPANY,
    TAB_RENEWALS,
    TAB_PIPELINE,
    TAB_SUPPLIERS,
)


def service_menu_panel_key(tab_name: str) -> str | None:
    """Map Database & Tasks tab to the panel that owns a service-type combo, if any."""
    return {
        TAB_CLIENTS: "clients",
        TAB_COMPANY: "company",
        TAB_PIPELINE: "pipeline",
    }.get(tab_name)


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

        self.tabs = themed_tabview(self.body, command=self._on_tab_changed)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        for name in TAB_NAMES:
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self.tasks_panel = None
        self.clients_panel = None
        self.courier_panel = None
        self.month_panel = None
        self.renewals_panel = None
        self.pipeline_panel = None
        self.company_panel = None
        self.suppliers_panel = None

    def _ensure_lazy_panel(self, name: str) -> None:
        if name in self._lazy_panels:
            return
        if name == TAB_TASKS:
            self.tasks_panel = TaskPanel(self.tabs.tab(TAB_TASKS), self.app, self.feedback)
            self.tasks_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.tasks_panel
        elif name == TAB_CLIENTS:
            self.clients_panel = ClientsExpiryPanel(self.tabs.tab(TAB_CLIENTS), self.app, self.feedback)
            self.clients_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.clients_panel
        elif name == TAB_COURIER:
            self.courier_panel = CourierPanel(self.tabs.tab(TAB_COURIER), self.app, self.feedback)
            self.courier_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.courier_panel
        elif name == TAB_MONTH:
            # MonthStatusPanel is lightweight with its own tree scrollbar; outer scroll not needed
            self.month_panel = MonthStatusPanel(
                self.tabs.tab(TAB_MONTH),
                self.app,
                showheight=12,
                title="Monthly tax status per client",
            )
            self.month_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.month_panel
        elif name == TAB_COMPANY:
            self.company_panel = CompanyDetailsPanel(self.tabs.tab(TAB_COMPANY), self.app, self.feedback)
            self.company_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.company_panel
        elif name == TAB_RENEWALS:
            self.renewals_panel = RenewalPanel(self.tabs.tab(TAB_RENEWALS), self.app, self.feedback)
            self.renewals_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.renewals_panel
        elif name == TAB_PIPELINE:
            self.pipeline_panel = ServicePipelinePanel(self.tabs.tab(TAB_PIPELINE), self.app, self.feedback)
            self.pipeline_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.pipeline_panel
        elif name == TAB_SUPPLIERS:
            self.suppliers_panel = SuppliersPanel(self.tabs.tab(TAB_SUPPLIERS), self.app, self.feedback)
            self.suppliers_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.suppliers_panel

    def _on_tab_changed(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = ""
        self._ensure_lazy_panel(current)
        self.refresh_active_tab(current)

    def refresh_active_tab(self, tab_name: str | None = None) -> None:
        """Reload data for the selected tab only (not all eight panels)."""
        if tab_name is None:
            try:
                tab_name = self.tabs.get()
            except Exception:
                tab_name = TAB_TASKS
        self._refresh_service_menus(tab_name)
        if tab_name == TAB_TASKS and self.tasks_panel is not None:
            self.tasks_panel.refresh()
        elif tab_name == TAB_COURIER and self.courier_panel is not None:
            self.courier_panel.refresh()
        elif tab_name == TAB_CLIENTS and self.clients_panel is not None:
            self.clients_panel.refresh()
        elif tab_name == TAB_MONTH and self.month_panel is not None:
            self.month_panel.refresh()
        elif tab_name == TAB_COMPANY and self.company_panel is not None:
            self.company_panel.refresh()
        elif tab_name == TAB_RENEWALS and self.renewals_panel is not None:
            self.renewals_panel.refresh()
        elif tab_name == TAB_PIPELINE and self.pipeline_panel is not None:
            self.pipeline_panel.refresh()
        elif tab_name == TAB_SUPPLIERS and self.suppliers_panel is not None:
            self.suppliers_panel.refresh()

    def _refresh_active_tab(self, tab_name: str) -> None:
        self.refresh_active_tab(tab_name)

    def _require_company_panel(self) -> CompanyDetailsPanel:
        self._ensure_lazy_panel(TAB_COMPANY)
        assert self.company_panel is not None
        return self.company_panel

    def on_show(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = TAB_TASKS
        self._ensure_lazy_panel(current)
        self.refresh_active_tab(current)

    def open_company_details(self, client_name: str) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.select_client(client_name)
        self.refresh_active_tab(TAB_COMPANY)

    def open_company_tax_ids(self, client_name: str) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.select_client(client_name)
        panel.tabs.set(SUBTAB_TAX_IDS)
        self.refresh_active_tab(TAB_COMPANY)

    def open_accounting_setup(self) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.tabs.set(SUBTAB_ACCOUNTING)
        self.refresh_active_tab(TAB_COMPANY)

    def open_vo_csh_setup(self) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.tabs.set(SUBTAB_VO_CSH_SETUP)
        self.refresh_active_tab(TAB_COMPANY)

    def open_company_vo_csh(self, client_name: str) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.select_client(client_name)
        panel.tabs.set(SUBTAB_VO_CSH)
        self.refresh_active_tab(TAB_COMPANY)

    def open_task(self, task_id: int) -> None:
        self.tabs.set(TAB_TASKS)
        self._ensure_lazy_panel(TAB_TASKS)
        if self.tasks_panel is not None:
            self.tasks_panel.select_task(task_id)

    def open_renewal(self, client_name: str) -> None:
        self._ensure_lazy_panel(TAB_RENEWALS)
        self.tabs.set(TAB_RENEWALS)
        assert self.renewals_panel is not None
        self.renewals_panel.select_client(client_name)
        self.renewals_panel.refresh()

    def open_pipeline(self) -> None:
        self._ensure_lazy_panel(TAB_PIPELINE)
        self.tabs.set(TAB_PIPELINE)
        if self.pipeline_panel is not None:
            self.pipeline_panel.refresh()

    def refresh_all(self) -> None:
        """Backward-compatible alias — refreshes only the active tab."""
        if not hasattr(self, "tabs"):
            return
        self.refresh_active_tab()

    def sync_service_menus(self) -> None:
        """Update service-type combobox values on constructed panels without full tab refresh."""
        types = self.app.db.list_service_types()
        if self.clients_panel is not None:
            combo = self.clients_panel.expiry_type
            combo.configure(values=types)
            if combo.get() not in types:
                combo.set(types[0] if types else "")
        if self.company_panel is not None:
            combo = getattr(self.company_panel, "service_type", None)
            if combo is not None:
                combo.configure(values=types)
                if combo.get() not in types:
                    combo.set(types[0] if types else "")
        if self.pipeline_panel is not None:
            combo = self.pipeline_panel.pipe_service
            combo.configure(values=types)
            if combo.get() not in types:
                combo.set(types[0] if types else "")

    def _refresh_service_menus(self, tab_name: str) -> None:
        panel_key = service_menu_panel_key(tab_name)
        if panel_key is None:
            return
        types = self.app.db.list_service_types()
        if panel_key == "clients" and self.clients_panel is not None:
            combo = self.clients_panel.expiry_type
            combo.configure(values=types)
            if combo.get() not in types:
                combo.set(types[0] if types else "")
        elif panel_key == "company" and self.company_panel is not None:
            combo = getattr(self.company_panel, "service_type", None)
            if combo is not None:
                combo.configure(values=types)
                if combo.get() not in types:
                    combo.set(types[0] if types else "")
        elif panel_key == "pipeline" and self.pipeline_panel is not None:
            combo = self.pipeline_panel.pipe_service
            combo.configure(values=types)
            if combo.get() not in types:
                combo.set(types[0] if types else "")

    def _export_excel(self) -> None:
        from skyadmin_pro.ui.views.export_filter_dialog import ExportFilterDialog

        def _do_export(*, date_from=None, date_to=None, status=None, visible_only=False):
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
                path = export_to_excel(
                    self.app.db, target,
                    date_from=date_from, date_to=date_to, status=status,
                    visible_only=self._visible_sheet_columns() if visible_only else None,
                )
            except Exception as exc:
                self.feedback.error(f"Export failed: {exc}")
                messagebox.showerror("Export failed", str(exc), parent=self.winfo_toplevel())
                return
            self.feedback.success(f"Exported to {path.name}")
            self.app.set_status(f"Exported database to {path}")

        ExportFilterDialog(self.winfo_toplevel(), on_export=_do_export)

    def _visible_sheet_columns(self) -> dict[str, list[str]]:
        """Map export sheet name → visible DB fields (opt-in visible-only export).

        Only sheets whose panel tree is currently built contribute; the rest
        export complete. UI column ids that don't map to DB fields (derived
        values like document status) are ignored.
        """
        # (panel attr, tree attr, sheet name, {ui col id: db field})
        specs = (
            ("clients_panel", "client_tree", "Clients",
             {"company": "name", "contact": "contact_name", "email": "email", "status": "status"}),
            ("clients_panel", "doc_tree", "Documents",
             {"client": "client_name", "type": "document_type", "expiry": "expiry_date"}),
            ("tasks_panel", "tree", "Tasks",
             {"client": "client_name", "title": "title", "category": "category",
              "status": "status", "due": "due_date", "completed": "completed_at"}),
            ("courier_panel", "tree", "Courier",
             {"sent": "date_sent", "client": "client_name", "tracking": "tracking_number",
              "driver": "driver_name", "destination": "destination", "task": "task_title"}),
            ("pipeline_panel", "pipe_tree", "Pipeline",
             {"client": "client_name", "service": "service", "step": "step", "status": "status"}),
        )
        result: dict[str, list[str]] = {}
        for panel_attr, tree_attr, sheet, id_map in specs:
            panel = getattr(self, panel_attr, None)
            tree = getattr(panel, tree_attr, None) if panel is not None and tree_attr else None
            if tree is None or not hasattr(tree, "get_visible_columns"):
                continue
            try:
                visible = tree.get_visible_columns()
            except Exception:
                continue
            fields = [id_map[c] for c in visible if c in id_map]
            if fields:
                result[sheet] = fields
        # Suppliers panel hosts three tab tables — collect whichever tabs exist.
        suppliers = getattr(self, "suppliers_panel", None)
        if suppliers is not None:
            for tab_attr, tree_attr, sheet, id_map in (
                ("directory", "supplier_tree", "Suppliers",
                 {"name": "name", "company": "company_name", "contact": "contact", "notes": "notes"}),
                ("payments", "pay_tree", "Supplier Payments",
                 {"supplier": "supplier_name", "client": "client_name", "amount": "amount",
                  "due": "due_date", "paid": "paid", "paid_date": "paid_date", "notes": "notes"}),
                ("services", "supplier_svc_tree", "Supplier Services",
                 {"company": "company_name", "service": "service_type",
                  "expiry": "expiry_date", "notes": "notes"}),
            ):
                tab = getattr(suppliers, tab_attr, None)
                tree = getattr(tab, tree_attr, None) if tab is not None else None
                if tree is None or not hasattr(tree, "get_visible_columns"):
                    continue
                try:
                    visible = tree.get_visible_columns()
                except Exception:
                    continue
                fields = [id_map[c] for c in visible if c in id_map]
                if sheet == "Supplier Services" and fields and "supplier_name" not in fields:
                    # Tree is single-supplier context (no supplier column shown),
                    # but the sheet needs attribution — data always carries it.
                    fields = ["supplier_name", *fields]
                if fields:
                    result[sheet] = fields
        return result

    def _on_shortcut_export(self) -> None:
        self._export_excel()

    def _on_shortcut_new(self) -> None:
        try:
            self.tabs.set(TAB_CLIENTS)
        except Exception:
            pass
        self._ensure_lazy_panel(TAB_CLIENTS)
        if self.clients_panel is not None:
            self.clients_panel._open_client_dialog()

    def _on_shortcut_save(self) -> bool:
        """Save the obvious form on the active Database & Tasks tab.

        Returns True when a save was invoked, False when nothing applies.
        """
        try:
            tab = self.tabs.get()
        except Exception:
            return False
        self._ensure_lazy_panel(tab)
        if tab == TAB_TASKS and self.tasks_panel is not None:
            self.tasks_panel._save()
            return True
        if tab == TAB_COMPANY and self.company_panel is not None:
            return bool(self.company_panel._on_shortcut_save())
        return False

    def _on_shortcut_undo(self) -> None:
        self._ensure_lazy_panel(TAB_CLIENTS)
        if self.clients_panel is not None:
            self.clients_panel._undo_last()
