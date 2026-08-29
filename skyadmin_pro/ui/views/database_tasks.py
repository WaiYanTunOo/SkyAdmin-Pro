"""Database & Tasks: live task table, courier tracker, clients, and Excel export."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    ACCOUNTING_PRICING_SERVICES,
    COURIER_DRIVERS,
    GENERAL_RENEWAL_TEMPLATE_NAME,
    IMPORTANT_DOC_TYPES,
    NAV_OFFICE_HUB,
    PIPELINE_MAX_STEP,
    PIPELINE_STEPS,
    SERVICE_PROGRESS,
    TASK_CATEGORIES,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
    TAX_FILING_STATUSES,
    TAX_FILING_FIELDS,
    TAX_FILING_LABELS,
    TRANSACTION_RANGES,
    PAYMENT_STATUSES,
    renewal_template_for,
)
from skyadmin_pro.services.export import default_export_name, export_to_excel
from skyadmin_pro.services.file_ops import (
    copy_file,
    format_thousands,
    open_in_file_manager,
    parse_flexible_date,
    sanitize_amount,
)
from skyadmin_pro.services.snippets import effective_text, load_snippet_overrides
from skyadmin_pro.services.tracking import (
    classify_expiry,
    days_until,
    effective_expiry_date,
    expiry_label,
)
from skyadmin_pro.services.tax_ids_rollout import (
    apply_pricing_tier,
    infer_service_types,
    list_accounting_setup_rows,
    parse_document_types,
)
from skyadmin_pro.services.vo_csh_rollout import (
    infer_client_vo_csh_renewal_dates,
    infer_vo_csh_renewal_dates,
    list_vo_csh_setup_rows,
)
from skyadmin_pro.services.workflow import (
    copy_to_clipboard,
    create_client_workspace,
    repair_client_workspaces,
    resolve_client_folder,
)
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.theme import CARD_CONTENT_PADX, CARD_RADIUS, CARD_TITLE_SIZE, TEXT_FAINT, TEXT_MUTED
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import DatePickerField, FeedbackLabel, make_modal, MonthStatusPanel

NONE_TASK = "(none)"


def _fill_combo(combo: ctk.CTkComboBox, values: list[str], current: str = "") -> None:
    combo.configure(values=values or [""])
    combo.set(current)


class DatabaseTasksView(BaseView):
    title = "Database & Tasks"
    subtitle = "Offline SQLite tracking for clients, tasks, courier deliveries, and expiry dates."

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)

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

        self.tabs = ctk.CTkTabview(self.body, command=self.refresh_all)
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

        self.courier_panel = CourierPanel(self.tabs.tab("Courier Tracker"), self.app, self.feedback)
        self.courier_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.clients_panel = ClientsExpiryPanel(
            self.tabs.tab("Clients & Expiry"), self.app, self.feedback
        )
        self.clients_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        month_scroll = ctk.CTkScrollableFrame(
            self.tabs.tab("Monthly Tax Status"), fg_color="transparent"
        )
        month_scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        month_scroll.grid_columnconfigure(0, weight=1)
        self.month_panel = MonthStatusPanel(
            month_scroll,
            self.app,
            showheight=12,
            title="Monthly tax status per client",
        )
        self.month_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.company_panel = CompanyDetailsPanel(
            self.tabs.tab("Company Details"), self.app, self.feedback
        )
        self.company_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.renewals_panel = RenewalPanel(
            self.tabs.tab("Renewals"), self.app, self.feedback
        )
        self.renewals_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.pipeline_panel = ServicePipelinePanel(
            self.tabs.tab("Service Pipeline"), self.app, self.feedback
        )
        self.pipeline_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.suppliers_panel = SuppliersPanel(
            self.tabs.tab("Suppliers & AP"), self.app, self.feedback
        )
        self.suppliers_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def on_show(self) -> None:
        self.refresh_all()

    def open_company_details(self, client_name: str) -> None:
        self.tabs.set("Company Details")
        self.company_panel.select_client(client_name)
        self.company_panel.refresh()

    def open_company_tax_ids(self, client_name: str) -> None:
        self.tabs.set("Company Details")
        self.company_panel.select_client(client_name)
        self.company_panel.tabs.set("Tax IDs")
        self.company_panel.refresh()

    def open_accounting_setup(self) -> None:
        self.tabs.set("Company Details")
        self.company_panel.tabs.set("Accounting Setup")
        self.company_panel.refresh_accounting_setup()

    def open_vo_csh_setup(self) -> None:
        self.tabs.set("Company Details")
        self.company_panel.tabs.set("VO/CSH Setup")
        self.company_panel.refresh_vo_csh_setup()

    def open_company_vo_csh(self, client_name: str) -> None:
        self.tabs.set("Company Details")
        self.company_panel.select_client(client_name)
        self.company_panel.tabs.set("VO & CSH")
        self.company_panel.refresh()

    def open_task(self, task_id: int) -> None:
        self.tabs.set("Tasks")
        self.tasks_panel.select_task(task_id)

    def open_renewal(self, client_name: str) -> None:
        self.tabs.set("Renewals")
        self.renewals_panel.select_client(client_name)
        self.renewals_panel.refresh()

    def open_pipeline(self) -> None:
        self.tabs.set("Service Pipeline")
        self.pipeline_panel.refresh()

    def refresh_all(self) -> None:
        if not hasattr(self, "tasks_panel"):
            return
        self._refresh_service_menus()
        self.tasks_panel.refresh()
        self.courier_panel.refresh()
        self.clients_panel.refresh()
        self.month_panel.refresh()
        self.company_panel.refresh()
        self.renewals_panel.refresh()
        self.pipeline_panel.refresh()
        self.suppliers_panel.refresh()

    def _refresh_service_menus(self) -> None:
        types = self.app.db.list_service_types()
        for combo in (self.clients_panel.expiry_type, self.company_panel.service_type):
            combo.configure(values=types)
            if combo.get() not in types:
                combo.set(types[0])
        self.pipeline_panel.pipe_service.configure(values=types)

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


class TaskPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._editing_id: int | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.filter = ctk.CTkSegmentedButton(
            top,
            values=["Pending", "Completed", "All"],
            command=lambda _v: self.refresh(),
        )
        self.filter.set("Pending")
        self.filter.pack(side="left")

        tree_card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        tree_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        tree_card.grid_columnconfigure(0, weight=1)
        tree_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            tree_card,
            text="Tasks",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.tree = ThemedTreeview(
            tree_card,
            columns=(
                ("client", "Client", 140),
                ("title", "Title", 240),
                ("category", "Category", 120),
                ("status", "Status", 90),
                ("due", "Due date", 100),
                ("completed", "Completed", 130),
            ),
            on_select=self._on_select,
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        form = ctk.CTkScrollableFrame(self, corner_radius=12, width=320)
        form.grid(row=1, column=1, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Task details", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 8)
        )
        self.status_label = ctk.CTkLabel(form, text="Status: new", text_color=TEXT_MUTED)
        self.status_label.grid(row=1, column=0, sticky="w", padx=16)

        ctk.CTkLabel(form, text="Client").grid(row=2, column=0, sticky="w", padx=16, pady=(10, 2))
        self.client_box = ctk.CTkComboBox(form, values=[""])
        self.client_box.grid(row=3, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(form, text="Title").grid(row=4, column=0, sticky="w", padx=16, pady=(10, 2))
        self.title_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.title_var).grid(row=5, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(form, text="Category").grid(row=6, column=0, sticky="w", padx=16, pady=(10, 2))
        self.category_menu = ctk.CTkOptionMenu(form, values=list(TASK_CATEGORIES))
        self.category_menu.set("General")
        self.category_menu.grid(row=7, column=0, sticky="w", padx=16)

        ctk.CTkLabel(form, text="Due date").grid(row=8, column=0, sticky="w", padx=16, pady=(10, 2))
        self.due_var = ctk.StringVar()
        DatePickerField(form, var=self.due_var).grid(row=9, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(form, text="Notes").grid(row=10, column=0, sticky="w", padx=16, pady=(10, 2))
        self.notes = ctk.CTkTextbox(form, height=90)
        self.notes.grid(row=11, column=0, sticky="ew", padx=16)

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=12, column=0, sticky="ew", padx=16, pady=(14, 14))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="New", command=self._new).grid(
            row=0, column=0, sticky="ew", padx=(0, 4), pady=3
        )
        ctk.CTkButton(buttons, text="Save", command=self._save).grid(
            row=0, column=1, sticky="ew", padx=(4, 0), pady=3
        )
        ctk.CTkButton(buttons, text="Mark complete", command=self._complete).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=3
        )
        ctk.CTkButton(
            buttons,
            text="Reopen",
            fg_color="transparent",
            border_width=1,
            command=self._reopen,
        ).grid(row=2, column=0, sticky="ew", padx=(0, 4), pady=3)
        ctk.CTkButton(
            buttons,
            text="Delete",
            fg_color="transparent",
            border_width=1,
            command=self._delete,
        ).grid(row=2, column=1, sticky="ew", padx=(4, 0), pady=3)

    def refresh(self) -> None:
        self.tree.apply_theme()
        names = self.app.db.list_client_names()
        current = self.client_box.get()
        _fill_combo(self.client_box, names, current)

        choice = self.filter.get()
        status = None
        if choice == "Pending":
            status = TASK_STATUS_PENDING
        elif choice == "Completed":
            status = TASK_STATUS_COMPLETED
        tasks = self.app.db.list_tasks(status=status)

        rows, iids, tags = [], [], []
        for task in tasks:
            rows.append(
                (
                    task.get("client_name") or "—",
                    task.get("title") or "",
                    task.get("category") or "",
                    (task.get("status") or "").title(),
                    task.get("due_date") or "—",
                    (task.get("completed_at") or "—")[:16],
                )
            )
            iids.append(str(task["id"]))
            tags.append(("completed",) if task.get("status") == TASK_STATUS_COMPLETED else ())
        self.tree.set_rows(rows, iids=iids, tags=tags)

    def _on_select(self, iid: str | None) -> None:
        if iid is None:
            return
        task = self.app.db.get_task(int(iid))
        if not task:
            return
        self._editing_id = int(task["id"])
        self.client_box.set(task.get("client_name") or "")
        self.title_var.set(task.get("title") or "")
        category = task.get("category") or "General"
        if category not in TASK_CATEGORIES:
            category = category.title() if category.title() in TASK_CATEGORIES else "General"
        self.category_menu.set(category)
        self.due_var.set(task.get("due_date") or "")
        self.notes.delete("1.0", "end")
        if task.get("description"):
            self.notes.insert("1.0", task["description"])
        self.status_label.configure(text=f"Status: {task.get('status', 'pending')}")

    def select_task(self, task_id: int) -> None:
        iid = str(task_id)
        if not self.tree.tree.exists(iid):
            # The task may be hidden by the current filter — reload first.
            self.refresh()
        if self.tree.tree.exists(iid):
            self.tree.tree.selection_set(iid)
            self.tree.tree.see(iid)
            self._on_select(iid)
        else:
            self.feedback.info("That task is not in the current filter.")

    def _new(self) -> None:
        self._editing_id = None
        self.title_var.set("")
        self.due_var.set("")
        self.notes.delete("1.0", "end")
        self.category_menu.set("General")
        self.client_box.set("")
        self.status_label.configure(text="Status: new")
        self.tree.tree.selection_remove(*self.tree.tree.selection())

    def _client_id(self) -> int | None:
        name = self.client_box.get().strip()
        if not name:
            return None
        return self.app.db.get_or_create_client(name)

    def _due_date(self) -> str | None:
        raw = self.due_var.get().strip()
        if not raw:
            return None
        parsed = parse_flexible_date(raw)
        if not parsed:
            raise ValueError("Enter a valid due date (YYYY-MM-DD or DD/MM/YYYY).")
        return parsed

    def _save(self) -> None:
        title = self.title_var.get().strip()
        if not title:
            self.feedback.error("Enter a task title.")
            return
        try:
            due = self._due_date()
            client_id = self._client_id()
            notes = self.notes.get("1.0", "end").strip()
            if self._editing_id is None:
                task_id = self.app.db.add_task(
                    title=title,
                    client_id=client_id,
                    description=notes,
                    category=self.category_menu.get(),
                    due_date=due,
                )
                self._editing_id = task_id
                self.feedback.success("Task added.")
            else:
                self.app.db.update_task(
                    self._editing_id,
                    title=title,
                    client_id=client_id,
                    description=notes,
                    category=self.category_menu.get(),
                    due_date=due,
                )
                self.feedback.success("Task updated.")
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        saved_status = "pending"
        if self._editing_id is not None:
            task = self.app.db.get_task(self._editing_id)
            if task:
                saved_status = task.get("status") or "pending"
        self.status_label.configure(text=f"Status: {saved_status}")
        self.refresh()
        if self._editing_id is not None:
            try:
                self.tree.tree.selection_set(str(self._editing_id))
            except Exception:
                pass
        self.app.set_status("Tasks saved.")

    def _complete(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select or save a task first.")
            return
        self.app.db.set_task_status(self._editing_id, TASK_STATUS_COMPLETED)
        self.feedback.success("Marked as completed.")
        self.refresh()
        self.status_label.configure(text="Status: completed")

    def _reopen(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select a task first.")
            return
        self.app.db.set_task_status(self._editing_id, TASK_STATUS_PENDING)
        self.feedback.success("Task reopened.")
        self.refresh()
        self.status_label.configure(text="Status: pending")

    def _delete(self) -> None:
        if self._editing_id is None:
            self.feedback.error("Select a task first.")
            return
        if not messagebox.askyesno(
            "Delete task",
            "Delete this task? Courier logs linked to it will be kept.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_task(self._editing_id)
        self.feedback.success("Task deleted.")
        self._new()
        self.refresh()


class CourierPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        tree_card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        tree_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tree_card.grid_columnconfigure(0, weight=1)
        tree_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            tree_card,
            text="Courier deliveries",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.tree = ThemedTreeview(
            tree_card,
            columns=(
                ("sent", "Date sent", 110),
                ("client", "Client", 140),
                ("tracking", "Tracking no.", 160),
                ("driver", "Driver", 110),
                ("destination", "Destination", 160),
                ("task", "Related task", 160),
            ),
        )
        self.tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        form = ctk.CTkScrollableFrame(self, corner_radius=12, width=320)
        form.grid(row=0, column=1, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form, text="Log outgoing delivery", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        ctk.CTkLabel(form, text="Client").grid(row=1, column=0, sticky="w", padx=16, pady=(4, 2))
        self.client_box = ctk.CTkComboBox(form, values=[""])
        self.client_box.grid(row=2, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(form, text="Tracking number").grid(
            row=3, column=0, sticky="w", padx=16, pady=(10, 2)
        )
        self.tracking_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.tracking_var).grid(
            row=4, column=0, sticky="ew", padx=16
        )

        ctk.CTkLabel(form, text="Driver (Grab / Lalamove)").grid(
            row=5, column=0, sticky="w", padx=16, pady=(10, 2)
        )
        self.driver_box = ctk.CTkComboBox(form, values=list(COURIER_DRIVERS))
        self.driver_box.set("Grab")
        self.driver_box.grid(row=6, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(form, text="Date sent").grid(row=7, column=0, sticky="w", padx=16, pady=(10, 2))
        self.sent_var = ctk.StringVar(value=date.today().isoformat())
        DatePickerField(form, var=self.sent_var).grid(row=8, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(form, text="Destination").grid(
            row=9, column=0, sticky="w", padx=16, pady=(10, 2)
        )
        self.dest_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.dest_var).grid(row=10, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(form, text="Related task").grid(
            row=11, column=0, sticky="w", padx=16, pady=(10, 2)
        )
        self.task_menu = ctk.CTkOptionMenu(form, values=[NONE_TASK])
        self.task_menu.set(NONE_TASK)
        self.task_menu.grid(row=12, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(form, text="Notes").grid(row=13, column=0, sticky="w", padx=16, pady=(10, 2))
        self.notes = ctk.CTkTextbox(form, height=70)
        self.notes.grid(row=14, column=0, sticky="ew", padx=16)

        ctk.CTkButton(form, text="Log delivery", command=self._log).grid(
            row=15, column=0, sticky="ew", padx=16, pady=(14, 6)
        )
        ctk.CTkButton(
            form,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete,
        ).grid(row=16, column=0, sticky="ew", padx=16, pady=(0, 14))

        self._task_lookup: dict[str, int] = {}

    def refresh(self) -> None:
        self.tree.apply_theme()
        _fill_combo(self.client_box, self.app.db.list_client_names(), self.client_box.get())
        pending = self.app.db.list_tasks(status=TASK_STATUS_PENDING)
        self._task_lookup = {f"#{item['id']}  {item['title']}": int(item["id"]) for item in pending}
        values = [NONE_TASK, *self._task_lookup.keys()]
        current = self.task_menu.get()
        self.task_menu.configure(values=values)
        self.task_menu.set(current if current in values else NONE_TASK)

        logs = self.app.db.list_courier_logs()
        self.tree.set_rows(
            [
                (
                    item.get("date_sent") or "—",
                    item.get("client_name") or "—",
                    item.get("tracking_number") or "",
                    item.get("driver_name") or "—",
                    item.get("destination") or "—",
                    item.get("task_title") or "—",
                )
                for item in logs
            ],
            iids=[str(item["id"]) for item in logs],
        )

    def _log(self) -> None:
        tracking = self.tracking_var.get().strip()
        if not tracking:
            self.feedback.error("Enter a tracking number.")
            return
        sent = parse_flexible_date(self.sent_var.get())
        if not sent:
            self.feedback.error("Enter a valid date sent.")
            return
        client_name = self.client_box.get().strip()
        client_id = self.app.db.get_or_create_client(client_name) if client_name else None
        task_choice = self.task_menu.get()
        task_id = self._task_lookup.get(task_choice)
        try:
            self.app.db.add_courier_log(
                tracking_number=tracking,
                driver_name=self.driver_box.get(),
                date_sent=sent,
                client_id=client_id,
                task_id=task_id,
                destination=self.dest_var.get(),
                notes=self.notes.get("1.0", "end").strip(),
            )
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Logged {tracking} ({self.driver_box.get()}).")
        self.tracking_var.set("")
        self.dest_var.set("")
        self.notes.delete("1.0", "end")
        self.refresh()

    def _delete(self) -> None:
        iid = self.tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a courier log first.")
            return
        if not messagebox.askyesno(
            "Delete courier log", "Remove this delivery record?", parent=self.winfo_toplevel()
        ):
            return
        self.app.db.delete_courier_log(int(iid))
        self.feedback.success("Courier log deleted.")
        self.refresh()


class ClientsExpiryPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS)
        left.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        left.grid_columnconfigure(0, weight=1)
        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(title_row, text="Company List", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.search_var = ctk.StringVar()
        self._search_after: str | None = None
        self.search_var.trace_add("write", lambda *_args: self._debounced_search())
        ctk.CTkEntry(
            title_row,
            textvariable=self.search_var,
            placeholder_text="Search name / email",
            width=230,
        ).grid(row=0, column=1, sticky="e", padx=(12, 0))
        ctk.CTkButton(
            title_row,
            text="Export to Excel",
            width=130,
            command=self._export_excel,
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))
        self.client_tree = ThemedTreeview(
            left,
            columns=(
                ("company", "Company name", 210),
                ("contact", "Contact", 150),
                ("email", "Email", 220),
                ("status", "Status", 90),
            ),
            showheight=9,
        )
        self.client_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        ctk.CTkButton(
            actions, text="Add / Edit client", width=125, command=self._open_client_dialog
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="View company details",
            width=155,
            fg_color="transparent",
            border_width=1,
            command=self._view_company_details,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Generate Workspace",
            width=150,
            command=self._generate_workspace,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Open client folder",
            width=135,
            fg_color="transparent",
            border_width=1,
            command=self._open_client_folder,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._delete_client,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Open Suppliers",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._open_suppliers,
        ).pack(side="left", padx=(8, 0))

        right = ctk.CTkFrame(scroll, corner_radius=CARD_RADIUS)
        right.grid(row=1, column=0, sticky="ew")
        right.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            right,
            text="Register document / service expiry",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(right, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(form, text="Client").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.expiry_client = ctk.CTkComboBox(form, values=[""])
        self.expiry_client.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Type").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.expiry_type = ctk.CTkOptionMenu(form, values=self.app.db.list_service_types())
        self.expiry_type.set(self.app.db.list_service_types()[0])
        self.expiry_type.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Expiry").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.expiry_var = ctk.StringVar()
        DatePickerField(form, var=self.expiry_var).grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkButton(right, text="Save expiry record", command=self._add_expiry).grid(
            row=2, column=0, sticky="ew", padx=16, pady=(8, 8)
        )

        self.doc_tree = ThemedTreeview(
            right,
            columns=(
                ("client", "Client", 140),
                ("type", "Type", 190),
                ("expiry", "Expiry", 100),
                ("status", "Status", 140),
            ),
            showheight=9,
        )
        self.doc_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        ctk.CTkButton(
            right,
            text="Delete selected record",
            fg_color="transparent",
            border_width=1,
            command=self._delete_document,
        ).grid(row=4, column=0, sticky="w", padx=16, pady=(0, 14))

    def refresh(self) -> None:
        self.client_tree.apply_theme()
        self.doc_tree.apply_theme()
        self._refresh_client_table()
        clients = self.app.db.list_clients()
        names = [item["name"] for item in clients]
        _fill_combo(self.expiry_client, names, self.expiry_client.get())

        documents = self.app.db.list_documents(expiring_only=True)
        rows, iids, tags = [], [], []
        for item in documents:
            eff = effective_expiry_date(
                item.get("expiry_date"), item.get("document_type")
            )
            left = days_until(eff)
            status = expiry_label(left) if left is not None else "—"
            tag = classify_expiry(left) if left is not None else "odd"
            rows.append(
                (
                    item.get("client_name") or "—",
                    item.get("document_type") or "—",
                    eff or "—",
                    status,
                )
            )
            iids.append(str(item["id"]))
            tags.append((tag,) if left is not None else ())
        self.doc_tree.set_rows(rows, iids=iids, tags=tags)

    def _debounced_search(self) -> None:
        # Wait for a pause in typing before hitting the database.
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except Exception:
                pass
        self._search_after = self.after(300, self._run_search)

    def _run_search(self) -> None:
        self._search_after = None
        self._refresh_client_table()

    def _refresh_client_table(self) -> None:
        clients = self.app.db.search_clients(self.search_var.get())
        rows, iids, tags = [], [], []
        for item in clients:
            rows.append(
                (
                    item.get("name") or "—",
                    item.get("contact_name") or "—",
                    item.get("email") or "—",
                    "Active" if item.get("status") != "inactive" else "Inactive",
                )
            )
            iids.append(str(item["id"]))
            tags.append(("inactive",) if item.get("status") == "inactive" else ())
        self.client_tree.set_rows(rows, iids=iids, tags=tags)

    def _export_excel(self) -> None:
        view = self.app._views.get("database_tasks")
        if view is not None and hasattr(view, "_export_excel"):
            view._export_excel()

    def _selected_client_name(self) -> str:
        selected = self.client_tree.selected_values()
        return selected[0] if selected else ""

    def _selected_client_id(self) -> int | None:
        iid = self.client_tree.selected_iid()
        return int(iid) if iid is not None else None

    def _open_client_dialog(self) -> None:
        client_id = self._selected_client_id()
        current = self.app.db.get_client(client_id) if client_id is not None else None
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("Edit client" if current else "Add client")
        top.resizable(False, False)
        top.geometry("460x340")
        top.update_idletasks()
        width, height = 460, 340
        x = (self.winfo_rootx() + self.winfo_width() // 2) - width // 2
        y = (self.winfo_rooty() + self.winfo_height() // 2) - height // 2
        top.geometry(f"{width}x{height}+{x}+{y}")
        top.deiconify()
        top.lift()
        top.focus_force()
        make_modal(top)
        body = ctk.CTkFrame(top, corner_radius=CARD_RADIUS)
        body.grid(row=0, column=0, padx=16, pady=16)
        body.grid_columnconfigure(1, weight=1)

        def _field_value(key: str) -> str:
            return (current or {}).get(key) or ""

        name_var = ctk.StringVar(value=_field_value("name"))
        contact_var = ctk.StringVar(value=_field_value("contact_name"))
        email_var = ctk.StringVar(value=_field_value("email"))
        status_var = ctk.StringVar(
            value=("Inactive" if current.get("status") == "inactive" else "Active")
            if current
            else "Active"
        )
        for row, label, var in (
            (0, "Company name", name_var),
            (1, "Contact name", contact_var),
            (2, "Email", email_var),
        ):
            ctk.CTkLabel(body, text=label, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 10), pady=6
            )
            ctk.CTkEntry(body, textvariable=var, width=320).grid(
                row=row, column=1, sticky="ew", pady=6
            )
        ctk.CTkLabel(body, text="Status", anchor="w").grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=6
        )
        status_menu = ctk.CTkOptionMenu(body, values=["Active", "Inactive"], variable=status_var)
        status_menu.grid(row=3, column=1, sticky="ew", pady=6)

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ctk.CTkButton(
            buttons,
            text="Save",
            width=100,
            command=lambda: self._save_client_dialog(top, client_id, name_var, contact_var, email_var, status_var),
        ).pack(side="right")
        ctk.CTkButton(
            buttons,
            text="Cancel",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=top.destroy,
        ).pack(side="right", padx=(0, 8))

    def _save_client_dialog(
        self, top, client_id: int | None, name_var, contact_var, email_var, status_var
    ) -> None:
        name = name_var.get().strip()
        if not name:
            self.feedback.error("Enter a company name.")
            return
        contact = contact_var.get().strip()
        email = email_var.get().strip()
        status = "active" if status_var.get() == "Active" else "inactive"
        try:
            if client_id is None:
                cid = self.app.db.get_or_create_client(name)
                self.app.db.update_client(
                    cid, contact_name=contact, email=email, status=status
                )
                view = self.app._views.get("database_tasks")
                if view is not None and hasattr(view, "tasks_panel"):
                    view.tasks_panel.refresh()
            else:
                self.app.db.update_client(
                    client_id,
                    name=name,
                    contact_name=contact,
                    email=email,
                    status=status,
                )
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        top.destroy()
        self.feedback.success(f"Client saved: {name}")
        self.refresh()

    def _generate_workspace(self) -> None:
        name = self._selected_client_name()
        if not name:
            self.feedback.error("Select a client row to generate its workspace.")
            return
        try:
            self.app.db.get_or_create_client(name)
            folder = create_client_workspace(self.app.paths.clients, name)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(
            f"Workspace ready: {folder.name}/01_Company_Setup, 02_Accounting, 03_Visa"
        )
        self.refresh()
        try:
            open_in_file_manager(folder)
        except Exception as exc:
            self.feedback.info(str(exc))

    def _delete_client(self) -> None:
        iid = self.client_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a client first.")
            return
        if not messagebox.askyesno(
            "Delete client",
            "Delete this client? Its pipeline, renewal checklists, and month-close "
            "records are removed. Services, documents, and tasks keep their records "
            "but lose the client link.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_client(int(iid))
        self.feedback.success("Client deleted.")
        self.refresh()

    def _open_client_folder(self) -> None:
        name = self._selected_client_name()
        if not name:
            self.feedback.error("Select a client row first.")
            return
        try:
            self.app.db.get_or_create_client(name)
            folder = create_client_workspace(self.app.paths.clients, name)
            open_in_file_manager(folder)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Opened: {folder}")
        self.app.set_status(f"Opened client workspace: {folder}")

    def _open_suppliers(self) -> None:
        try:
            open_in_file_manager(self.app.paths.suppliers)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Opened: {self.app.paths.suppliers}")

    def _view_company_details(self) -> None:
        name = self._selected_client_name()
        if not name:
            self.feedback.error("Select a client row first.")
            return
        view = self.app._views.get("database_tasks")
        if view is not None and hasattr(view, "open_company_details"):
            view.open_company_details(name)
            self.feedback.info(f"Showing details for {name}")

    def _add_expiry(self) -> None:
        client = self.expiry_client.get().strip()
        if not client:
            self.feedback.error("Choose or type a client name.")
            return
        expiry = parse_flexible_date(self.expiry_var.get())
        if not expiry:
            self.feedback.error("Enter a valid expiry date.")
            return
        try:
            client_id = self.app.db.get_or_create_client(client)
            self.app.db.record_document(
                client_id=client_id,
                document_type=self.expiry_type.get(),
                file_name="",
                file_path="",
                expiry_date=expiry,
            )
        except Exception as exc:
            self.feedback.error(f"Could not record expiry: {exc}")
            return
        self.feedback.success(f"Expiry recorded for {client} ({expiry}).")
        self.expiry_var.set("")
        self.refresh()

    def _delete_document(self) -> None:
        iid = self.doc_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select an expiry record first.")
            return
        if not messagebox.askyesno(
            "Delete expiry record",
            "Delete this expiry record?\n\nLinked renewal tasks will also be removed.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_document(int(iid))
        self.feedback.success("Expiry record deleted.")
        self.refresh()


class CompanyDetailsPanel(ctk.CTkFrame):
    """Per-company overview: services, documents, tax IDs, filing statuses, VO & CSH."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._editing_service_id: int | None = None
        self._editing_doc_id: int | None = None
        self._filing_suspend_save = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        selector = ctk.CTkFrame(self, fg_color="transparent")
        selector.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        selector.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(selector, text="Company / Client:").grid(
            row=0, column=0, sticky="w"
        )
        self.company_box = ctk.CTkComboBox(selector, values=[""], command=self._on_company)
        self.company_box.grid(row=0, column=1, sticky="ew")
        self.company_info = ctk.CTkLabel(
            selector, text="", text_color=TEXT_MUTED, anchor="e"
        )
        self.company_info.grid(row=0, column=2, sticky="e", padx=(12, 0))
        ctk.CTkButton(
            selector,
            text="Missing docs workflow",
            width=180,
            command=self._missing_docs_workflow,
        ).grid(row=0, column=3, padx=(8, 0))

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        for name in (
            "Accounting Setup",
            "General",
            "Tax IDs",
            "Filing Statuses",
            "VO/CSH Setup",
            "VO & CSH",
            "Financial Docs",
        ):
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_propagate(False)

        setup_tab = self.tabs.tab("Accounting Setup")
        setup_scroll = ctk.CTkScrollableFrame(setup_tab, fg_color="transparent")
        setup_scroll.grid(row=0, column=0, sticky="nsew")
        setup_scroll.grid_columnconfigure(0, weight=1)
        self._accounting_setup_frame = self._build_accounting_setup(setup_scroll)
        self._accounting_setup_frame.grid(row=0, column=0, sticky="ew")

        # General tab — existing content
        general_tab = self.tabs.tab("General")
        general_scroll = ctk.CTkScrollableFrame(general_tab, fg_color="transparent")
        general_scroll.grid(row=0, column=0, sticky="nsew")
        general_scroll.grid_columnconfigure(0, weight=1)
        self._company_frame = self._build_company_info(general_scroll)
        self._company_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._services_frame = self._build_services(general_scroll)
        self._services_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._docs_frame = self._build_documents(general_scroll)
        self._docs_frame.grid(row=2, column=0, sticky="ew")

        # Tax IDs tab
        tax_ids_tab = self.tabs.tab("Tax IDs")
        tax_ids_scroll = ctk.CTkScrollableFrame(tax_ids_tab, fg_color="transparent")
        tax_ids_scroll.grid(row=0, column=0, sticky="nsew")
        tax_ids_scroll.grid_columnconfigure(0, weight=1)
        self._tax_ids_frame = self._build_tax_ids(tax_ids_scroll)
        self._tax_ids_frame.grid(row=0, column=0, sticky="ew")

        # Filing Statuses tab
        filing_tab = self.tabs.tab("Filing Statuses")
        filing_scroll = ctk.CTkScrollableFrame(filing_tab, fg_color="transparent")
        filing_scroll.grid(row=0, column=0, sticky="nsew")
        filing_scroll.grid_columnconfigure(0, weight=1)
        self._filing_frame = self._build_filing_statuses(filing_scroll)
        self._filing_frame.grid(row=0, column=0, sticky="ew")

        vo_setup_tab = self.tabs.tab("VO/CSH Setup")
        vo_setup_scroll = ctk.CTkScrollableFrame(vo_setup_tab, fg_color="transparent")
        vo_setup_scroll.grid(row=0, column=0, sticky="nsew")
        vo_setup_scroll.grid_columnconfigure(0, weight=1)
        self._vo_csh_setup_frame = self._build_vo_csh_setup(vo_setup_scroll)
        self._vo_csh_setup_frame.grid(row=0, column=0, sticky="ew")

        # VO & CSH tab
        vo_tab = self.tabs.tab("VO & CSH")
        vo_scroll = ctk.CTkScrollableFrame(vo_tab, fg_color="transparent")
        vo_scroll.grid(row=0, column=0, sticky="nsew")
        vo_scroll.grid_columnconfigure(0, weight=1)
        self._vo_frame = self._build_vo_csh(vo_scroll)
        self._vo_frame.grid(row=0, column=0, sticky="ew")

        # Financial Docs tab
        fin_tab = self.tabs.tab("Financial Docs")
        fin_scroll = ctk.CTkScrollableFrame(fin_tab, fg_color="transparent")
        fin_scroll.grid(row=0, column=0, sticky="nsew")
        fin_scroll.grid_columnconfigure(0, weight=1)
        self._fin_frame = self._build_financial_docs(fin_scroll)
        self._fin_frame.grid(row=0, column=0, sticky="ew")

    def _build_company_info(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Company info",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.company_name_label = ctk.CTkLabel(
            frame,
            text="—",
            anchor="w",
            wraplength=880,
            justify="left",
            font=ctk.CTkFont(weight="bold"),
        )
        self.company_name_label.grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 6)
        )

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.grid(row=2, column=0, sticky="ew", padx=16)
        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.info_reg_number = ctk.StringVar()
        self.info_director = ctk.StringVar()
        self.info_email = ctk.StringVar()
        self.info_contact = ctk.StringVar()
        self.info_capital = ctk.StringVar()
        self.info_vat = ctk.StringVar()
        self.info_address = ctk.StringVar()

        labels = (
            (0, 0, "Registration number", self.info_reg_number),
            (0, 2, "Director", self.info_director),
            (2, 0, "Company email", self.info_email),
            (2, 2, "Contact number", self.info_contact),
            (4, 0, "Registered capital", self.info_capital),
            (4, 2, "VAT registration", self.info_vat),
        )
        for row, col, label, var in labels:
            ctk.CTkLabel(grid, text=label).grid(
                row=row, column=col, sticky="w", pady=(2, 2)
            )
            ctk.CTkEntry(grid, textvariable=var).grid(
                row=row + 1,
                column=col,
                columnspan=2,
                sticky="ew",
                padx=(0, 12),
                pady=(0, 4),
            )

        ctk.CTkLabel(grid, text="Business address").grid(
            row=6, column=0, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(grid, textvariable=self.info_address).grid(
            row=7, column=0, columnspan=4, sticky="ew", padx=(0, 12), pady=(0, 4)
        )

        ctk.CTkLabel(frame, text="Business objectives").grid(
            row=3, column=0, sticky="w", padx=16, pady=(6, 2)
        )
        self.info_objectives = ctk.CTkTextbox(frame, height=80, wrap="word")
        self.info_objectives.grid(
            row=4, column=0, sticky="ew", padx=16, pady=(0, 8)
        )

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 14))
        buttons.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            buttons, text="Save company info", width=150, command=self._save_company_info
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            buttons,
            text="Company name is managed in the Clients & Expiry tab.",
            text_color=TEXT_MUTED,
        ).grid(row=0, column=1, sticky="e", padx=(12, 0))
        return frame

    def _save_company_info(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        try:
            self.app.db.update_client(
                client_id,
                email=self.info_email.get().strip(),
                registration_number=self.info_reg_number.get().strip(),
                director=self.info_director.get().strip(),
                contact_number=self.info_contact.get().strip(),
                registered_capital=self.info_capital.get().strip(),
                vat_registration=self.info_vat.get().strip(),
                business_address=self.info_address.get().strip(),
                business_objectives=self.info_objectives.get("1.0", "end").strip(),
            )
        except Exception as exc:
            self.feedback.error(f"Could not save company info: {exc}")
            return
        self.feedback.success("Company info saved.")
        self.refresh()

    def _build_services(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Services — expiry, payment & progress",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.service_tree = ThemedTreeview(
            frame,
            columns=(
                ("type", "Service", 150),
                ("start", "Start", 95),
                ("expiry", "Expiry", 95),
                ("payment", "Payment", 95),
                ("amount", "Amount", 85),
                ("progress", "Progress", 95),
                ("paid", "Paid", 55),
            ),
            on_double_click=self._edit_service,
        )
        self.service_tree.tree.configure(height=7)
        self.service_tree.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        form.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.service_status_label = ctk.CTkLabel(
            form, text="New service record", text_color=TEXT_MUTED
        )
        self.service_status_label.grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(4, 6)
        )

        ctk.CTkLabel(form, text="Service type").grid(
            row=1, column=0, sticky="w", pady=(2, 2)
        )
        self.service_type = ctk.CTkOptionMenu(form, values=self.app.db.list_service_types())
        self.service_type.set(self.app.db.list_service_types()[0])
        self.service_type.grid(row=2, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Start date").grid(
            row=1, column=1, sticky="w", pady=(2, 2)
        )
        self.service_start = ctk.StringVar()
        DatePickerField(form, var=self.service_start).grid(
            row=2, column=1, sticky="ew", padx=(0, 6)
        )

        ctk.CTkLabel(form, text="Expiry date").grid(
            row=1, column=2, sticky="w", pady=(2, 2)
        )
        self.service_expiry = ctk.StringVar()
        DatePickerField(form, var=self.service_expiry).grid(
            row=2, column=2, sticky="ew", padx=(0, 6)
        )

        ctk.CTkLabel(form, text="Payment date").grid(
            row=1, column=3, sticky="w", pady=(2, 2)
        )
        self.service_payment = ctk.StringVar()
        DatePickerField(form, var=self.service_payment).grid(
            row=2, column=3, sticky="ew"
        )

        ctk.CTkLabel(form, text="Amount").grid(
            row=3, column=0, sticky="w", pady=(10, 2)
        )
        self.service_amount = ctk.StringVar()
        amount_entry = ctk.CTkEntry(form, textvariable=self.service_amount)
        amount_entry.bind(
            "<FocusOut>",
            lambda _e: self.service_amount.set(
                format_thousands(self.service_amount.get())
            ),
        )
        amount_entry.grid(row=4, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Progress").grid(
            row=3, column=1, sticky="w", pady=(10, 2)
        )
        self.service_progress = ctk.CTkOptionMenu(form, values=list(SERVICE_PROGRESS))
        self.service_progress.set(SERVICE_PROGRESS[0])
        self.service_progress.grid(row=4, column=1, sticky="ew", padx=(0, 6))

        self.service_paid = ctk.CTkCheckBox(form, text="Payment received")
        self.service_paid.grid(row=3, column=2, sticky="w", pady=(10, 2))

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=4, column=2, columnspan=2, sticky="ew")
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="Save service", command=self._save_service).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ctk.CTkButton(
            buttons,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete_service,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        renew_buttons = ctk.CTkFrame(form, fg_color="transparent")
        renew_buttons.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        renew_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            renew_buttons,
            text="Renew / extend service…",
            fg_color="transparent",
            border_width=1,
            command=self._renew_service,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            renew_buttons,
            text="Renewal history",
            fg_color="transparent",
            border_width=1,
            command=self._renewal_history,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        return frame

    def _build_documents(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Important documents",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.doc_tree = ThemedTreeview(
            frame,
            columns=(
                ("type", "Document", 170),
                ("file", "File", 170),
                ("expiry", "Expiry", 95),
                ("added", "Added", 120),
            ),
            on_double_click=self._edit_document,
        )
        self.doc_tree.tree.configure(height=7)
        self.doc_tree.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        form.grid_columnconfigure((0, 1, 2), weight=1)

        self.document_status_label = ctk.CTkLabel(
            form, text="New document record", text_color=TEXT_MUTED
        )
        self.document_status_label.grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(4, 6)
        )

        ctk.CTkLabel(form, text="Document type").grid(
            row=1, column=0, sticky="w", pady=(2, 2)
        )
        self.doc_type = ctk.CTkOptionMenu(form, values=list(IMPORTANT_DOC_TYPES))
        self.doc_type.set(IMPORTANT_DOC_TYPES[0])
        self.doc_type.grid(row=2, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Expiry date (optional)").grid(
            row=1, column=1, sticky="w", pady=(2, 2)
        )
        self.doc_expiry = ctk.StringVar()
        DatePickerField(form, var=self.doc_expiry).grid(
            row=2, column=1, sticky="ew", padx=(0, 6)
        )

        ctk.CTkLabel(form, text="File (pick or type)").grid(
            row=1, column=2, sticky="w", pady=(2, 2)
        )
        file_row = ctk.CTkFrame(form, fg_color="transparent")
        file_row.grid(row=2, column=2, sticky="ew", padx=(0, 6))
        file_row.grid_columnconfigure(0, weight=1)
        self.doc_file = ctk.StringVar()
        self.doc_path = ctk.StringVar()
        ctk.CTkEntry(file_row, textvariable=self.doc_file).grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkButton(
            file_row,
            text="Pick file…",
            width=90,
            command=self._pick_document_file,
        ).grid(row=0, column=1, padx=(6, 0))

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="Save document", command=self._save_document).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ctk.CTkButton(
            buttons,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete_document,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        return frame

    def _build_accounting_setup(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        self._accounting_setup_rows: dict[str, dict] = {}
        self._selected_accounting_setup_id: int | None = None

        ctk.CTkLabel(
            frame,
            text="Accounting clients — Tax IDs rollout",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            frame,
            text=(
                "Clients with annual/monthly accounting or tax-filing documents. "
                "Infer service type from documents, then open Tax IDs to set transaction "
                "volume, tax ID, and pricing."
            ),
            wraplength=760,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        ctk.CTkLabel(toolbar, text="Show", anchor="w").grid(row=0, column=0, padx=(0, 8))
        self.accounting_setup_filter = ctk.CTkOptionMenu(
            toolbar,
            values=["All", "Needs setup", "Ready"],
            command=lambda _c: self.refresh_accounting_setup(),
            width=140,
        )
        self.accounting_setup_filter.set("All")
        self.accounting_setup_filter.grid(row=0, column=1, sticky="w")
        self.accounting_setup_summary = ctk.CTkLabel(
            toolbar, text="", text_color=TEXT_MUTED, anchor="w"
        )
        self.accounting_setup_summary.grid(row=0, column=2, sticky="ew", padx=(16, 0))
        toolbar.grid_columnconfigure(2, weight=1)

        self.accounting_setup_tree = ThemedTreeview(
            frame,
            columns=(
                ("company", "Company", 220),
                ("status", "Setup", 90),
                ("service", "Service type", 140),
                ("suggested", "Suggested", 140),
                ("volume", "Txn volume", 170),
                ("tax_id", "Tax ID", 120),
                ("docs", "Accounting docs", 220),
            ),
            on_select=self._on_accounting_setup_select,
            on_double_click=self._open_selected_accounting_tax_ids,
            showheight=10,
        )
        self.accounting_setup_tree.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 14))
        ctk.CTkButton(
            actions,
            text="Open Tax IDs",
            width=120,
            command=self._open_selected_accounting_tax_ids,
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Infer service type",
            width=140,
            command=self._infer_selected_service_type,
        ).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Infer all missing",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=self._infer_all_service_types,
        ).grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Apply pricing tier",
            width=140,
            fg_color="transparent",
            border_width=1,
            command=self._apply_selected_pricing_tier,
        ).grid(row=0, column=3)
        return frame

    def refresh_accounting_setup(self) -> None:
        if not hasattr(self, "accounting_setup_tree"):
            return
        self.accounting_setup_tree.apply_theme()
        rows = list_accounting_setup_rows(self.app.db)
        ready = sum(1 for row in rows if not row.get("setup_missing"))
        self.accounting_setup_summary.configure(
            text=f"{ready} of {len(rows)} accounting client(s) ready for tax cycle"
        )
        filt = self.accounting_setup_filter.get()
        if filt == "Needs setup":
            rows = [row for row in rows if row.get("setup_missing")]
        elif filt == "Ready":
            rows = [row for row in rows if not row.get("setup_missing")]

        self._accounting_setup_rows = {}
        tree_rows = []
        iids = []
        tags = []
        for row in rows:
            iid = str(row["id"])
            self._accounting_setup_rows[iid] = row
            iids.append(iid)
            docs = parse_document_types(row.get("document_types"))
            short_docs = docs[0] if len(docs) == 1 else f"{len(docs)} doc type(s)" if docs else "—"
            tree_rows.append(
                (
                    row.get("name") or "",
                    row.get("setup_status") or "",
                    row.get("service_type") or "—",
                    row.get("suggested_service_type") or "—",
                    row.get("num_transactions") or "—",
                    row.get("tax_id") or "—",
                    short_docs,
                )
            )
            tag = ()
            if row.get("setup_status") == "Ready":
                tag = ("done",)
            elif row.get("setup_status") == "Almost":
                tag = ("watch",)
            elif row.get("setup_status") == "Needs setup":
                tag = ("urgent",)
            tags.append(tag)
        self.accounting_setup_tree.set_rows(tree_rows, iids=iids, tags=tags)

    def _on_accounting_setup_select(self, iid: str | None) -> None:
        self._selected_accounting_setup_id = int(iid) if iid else None

    def _selected_accounting_setup_row(self) -> dict | None:
        if self._selected_accounting_setup_id is None:
            return None
        return self._accounting_setup_rows.get(str(self._selected_accounting_setup_id))

    def _open_selected_accounting_tax_ids(self, _iid: str | None = None) -> None:
        row = self._selected_accounting_setup_row()
        if not row:
            self.feedback.error("Select an accounting client first.")
            return
        name = (row.get("name") or "").strip()
        self.select_client(name)
        self.tabs.set("Tax IDs")
        self.refresh()

    def _infer_selected_service_type(self) -> None:
        row = self._selected_accounting_setup_row()
        if not row:
            self.feedback.error("Select an accounting client first.")
            return
        suggested = (row.get("suggested_service_type") or "").strip()
        if not suggested:
            self.feedback.error("No service type can be inferred from this client's documents.")
            return
        if (row.get("service_type") or "").strip() and (
            row.get("service_type") or ""
        ).strip() != suggested:
            if not messagebox.askyesno(
                "Overwrite service type",
                f"Replace '{row.get('service_type')}' with inferred '{suggested}'?",
                parent=self.winfo_toplevel(),
            ):
                return
        self.app.db.update_client_fields(int(row["id"]), service_type=suggested)
        self.feedback.success(f"Service type set to {suggested}.")
        self.refresh_accounting_setup()
        if self._selected_client_id() == int(row["id"]):
            self.refresh()

    def _infer_all_service_types(self) -> None:
        pending = sum(
            1
            for row in list_accounting_setup_rows(self.app.db)
            if not (row.get("service_type") or "").strip()
            and (row.get("suggested_service_type") or "").strip()
        )
        if pending == 0:
            self.feedback.info("No clients need service-type inference.")
            return
        if not messagebox.askyesno(
            "Infer service types",
            f"Infer service type from documents for {pending} client(s) "
            "that do not have one yet?",
            parent=self.winfo_toplevel(),
        ):
            return
        updated = infer_service_types(self.app.db, only_missing=True)
        self.feedback.success(f"Inferred service type for {updated} client(s).")
        self.refresh_accounting_setup()
        self.refresh()

    def _apply_selected_pricing_tier(self) -> None:
        row = self._selected_accounting_setup_row()
        if not row:
            self.feedback.error("Select an accounting client first.")
            return
        client_id = int(row["id"])
        if not (row.get("service_type") or "").strip():
            self.feedback.error("Set service type first (use Infer service type).")
            return
        if not (row.get("num_transactions") or "").strip():
            self.feedback.error(
                "Set transaction volume in Tax IDs before applying pricing."
            )
            return
        if not apply_pricing_tier(self.app.db, client_id):
            self.feedback.error("No pricing tier found for this service and volume.")
            return
        self.feedback.success("Pricing tier applied (fee, SLA, headcount).")
        self.refresh_accounting_setup()
        if self._selected_client_id() == client_id:
            self.refresh()

    def _build_tax_ids(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Tax Identity & Service Contract",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure((0, 1), weight=1)

        self.tax_id_var = ctk.StringVar()
        self.cred_pw_var = ctk.StringVar()
        self.vat_reg_date_var = ctk.StringVar()
        self.service_fee_var = ctk.StringVar()
        self.sla_var = ctk.StringVar()
        self.headcount_var = ctk.StringVar()

        ctk.CTkLabel(form, text="Tax ID").grid(row=0, column=0, columnspan=2, sticky="w", pady=(2, 2))
        ctk.CTkEntry(form, textvariable=self.tax_id_var).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )

        ctk.CTkLabel(form, text="VAT Registered").grid(
            row=2, column=0, sticky="w", pady=(6, 2)
        )
        self.vat_registered_var = ctk.BooleanVar()
        ctk.CTkCheckBox(form, text="Yes", variable=self.vat_registered_var).grid(
            row=3, column=0, sticky="w", pady=(0, 4)
        )
        ctk.CTkLabel(form, text="VAT Registration Date").grid(
            row=2, column=1, sticky="w", pady=(6, 2)
        )
        DatePickerField(form, var=self.vat_reg_date_var).grid(
            row=3, column=1, sticky="ew", pady=(0, 4)
        )

        ctk.CTkLabel(form, text="Service Type").grid(
            row=4, column=0, sticky="w", pady=(6, 2)
        )
        self.acct_service_type = ctk.CTkOptionMenu(
            form, values=["", *ACCOUNTING_PRICING_SERVICES]
        )
        self.acct_service_type.grid(row=5, column=0, sticky="ew", padx=(0, 12), pady=(0, 4))
        ctk.CTkLabel(form, text="Transaction Volume").grid(
            row=4, column=1, sticky="w", pady=(6, 2)
        )
        self.acct_txn_volume = ctk.CTkOptionMenu(form, values=list(TRANSACTION_RANGES))
        self.acct_txn_volume.grid(row=5, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="Service Fee (THB)").grid(
            row=6, column=0, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(form, textvariable=self.service_fee_var).grid(
            row=7, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="Payment Status").grid(
            row=6, column=1, sticky="w", pady=(6, 2)
        )
        self.acct_payment_status = ctk.CTkOptionMenu(form, values=list(PAYMENT_STATUSES))
        self.acct_payment_status.grid(row=7, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="SLA (hours)").grid(
            row=8, column=0, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(form, textvariable=self.sla_var).grid(
            row=9, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="Headcount").grid(
            row=8, column=1, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(form, textvariable=self.headcount_var).grid(
            row=9, column=1, sticky="ew", pady=(0, 4)
        )

        cred_card = ctk.CTkFrame(frame, corner_radius=12)
        cred_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 8))
        cred_card.grid_columnconfigure(0, weight=1)
        self._client_cred_rows: dict[str, dict] = {}
        self._selected_client_cred_id: int | None = None

        ctk.CTkLabel(
            cred_card,
            text="Client portal logins (read-only)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))
        ctk.CTkLabel(
            cred_card,
            text="DBD, RD, IRD, and other types — edit in Office Hub → Passwords → Client DBD / RD.",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        self.client_cred_tree = ThemedTreeview(
            cred_card,
            columns=(
                ("type", "Type", 90),
                ("login", "Login ID", 140),
                ("portal", "Portal URL", 200),
            ),
            on_select=self._on_client_cred_select,
            showheight=4,
        )
        self.client_cred_tree.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))

        cred_detail = ctk.CTkFrame(cred_card, fg_color="transparent")
        cred_detail.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        cred_detail.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cred_detail, text="Password", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cred_pw_entry = ctk.CTkEntry(
            cred_detail, textvariable=self.cred_pw_var, show="*", state="disabled"
        )
        self.cred_pw_entry.grid(row=0, column=1, sticky="ew")
        ctk.CTkButton(
            cred_detail, text="Copy", width=70, command=self._copy_client_cred_password
        ).grid(row=0, column=2, padx=(8, 0))

        cred_actions = ctk.CTkFrame(cred_card, fg_color="transparent")
        cred_actions.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 12))
        ctk.CTkButton(
            cred_actions,
            text="Edit in Office Hub",
            width=140,
            command=self._open_office_hub_credentials,
        ).pack(side="left")

        ctk.CTkButton(
            frame, text="Save Tax IDs & Service Info", width=200,
            command=self._save_tax_ids,
        ).grid(row=3, column=0, sticky="w", padx=16, pady=(8, 14))

        self.acct_txn_volume.configure(command=self._on_txn_volume_change)
        return frame

    def _set_cred_password_display(self, password: str = "") -> None:
        self.cred_pw_entry.configure(state="normal")
        self.cred_pw_var.set(password or "—")
        self.cred_pw_entry.configure(state="disabled")

    def _load_client_credentials_display(self, client_id: int | None) -> None:
        self._selected_client_cred_id = None
        self._client_cred_rows = {}
        self._set_cred_password_display()
        if client_id is None:
            self.client_cred_tree.set_rows([])
            return
        rows = self.app.db.list_client_credentials(client_id=client_id)
        tree_rows = []
        iids = []
        for row in rows:
            iid = str(row["id"])
            self._client_cred_rows[iid] = row
            iids.append(iid)
            tree_rows.append(
                (
                    row.get("credential_type") or "",
                    row.get("login_id") or row.get("username") or row.get("registration_number") or "",
                    row.get("portal_url") or "",
                )
            )
        self.client_cred_tree.set_rows(tree_rows, iids=iids)
        if iids:
            self.client_cred_tree.tree.selection_set(iids[0])
            self.client_cred_tree.tree.focus(iids[0])
            self._on_client_cred_select(iids[0])

    def _on_client_cred_select(self, iid: str | None) -> None:
        if not iid:
            self._selected_client_cred_id = None
            self._set_cred_password_display()
            return
        row = self._client_cred_rows.get(str(iid))
        if not row:
            self._selected_client_cred_id = None
            self._set_cred_password_display()
            return
        self._selected_client_cred_id = int(iid)
        self._set_cred_password_display(row.get("password") or "")

    def _copy_client_cred_password(self) -> None:
        secret = self.cred_pw_var.get().strip()
        if not secret or secret == "—":
            self.feedback.error("No password stored for the selected login.")
            return
        copy_to_clipboard(secret)
        self.feedback.success("Password copied.")

    def _open_office_hub_credentials(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        client = self.app.db.get_client(client_id)
        name = (client or {}).get("name") or ""
        if not name:
            self.feedback.error("Select a company first.")
            return
        cred_type = None
        cred_id = self._selected_client_cred_id
        if cred_id is not None:
            row = self._client_cred_rows.get(str(cred_id))
            cred_type = (row or {}).get("credential_type")
        open_hub = getattr(self.app, "open_office_hub_client_credentials", None)
        if callable(open_hub):
            open_hub(name, credential_type=cred_type, credential_id=cred_id)
        else:
            self.app.show_view(NAV_OFFICE_HUB)

    def _on_txn_volume_change(self, choice: str) -> None:
        tier = self.app.db.lookup_pricing_by_range(
            choice,
            service_type=self.acct_service_type.get().strip() or None,
        )
        if not tier:
            return
        fee = tier.get("monthly_fee")
        sla = tier.get("sla_hours")
        hc = tier.get("headcount")
        fee_txt = f"{fee:,} THB/mo" if fee is not None else "not set"
        sla_txt = f"{sla}h" if sla is not None else "not set"
        hc_txt = str(hc) if hc is not None else "not set"
        current_fee = self.service_fee_var.get().strip()
        current_sla = self.sla_var.get().strip()
        current_hc = self.headcount_var.get().strip()
        # Only auto-fill if fields are empty or match a previous tier value
        if current_fee and current_sla and current_hc:
            import tkinter.messagebox as mb
            if not mb.askyesno(
                "Auto-fill pricing",
                f"Overwrite current values with pricing for '{choice}'?\n\n"
                f"Fee: {fee_txt} | SLA: {sla_txt} | HC: {hc_txt}",
                parent=self.winfo_toplevel(),
            ):
                return
        if fee is None and sla is None and hc is None:
            self.feedback.error(
                f"No pricing configured for '{choice}' — set it in Settings → Pricing matrix."
            )
            return
        if fee is not None:
            self.service_fee_var.set(str(fee))
        if sla is not None:
            self.sla_var.set(str(sla))
        if hc is not None:
            self.headcount_var.set(str(hc))

    def _save_tax_ids(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        vat_date_raw = self.vat_reg_date_var.get().strip()
        vat_date = None
        if vat_date_raw:
            vat_date = parse_flexible_date(vat_date_raw)
            if not vat_date:
                self.feedback.error("VAT registration date is not a valid date.")
                return
        try:
            self.app.db.update_client_fields(
                client_id,
                tax_id=self.tax_id_var.get().strip(),
                vat_registered=1 if self.vat_registered_var.get() else 0,
                vat_registered_date=vat_date,
                service_type=self.acct_service_type.get() or None,
                num_transactions=self.acct_txn_volume.get() or None,
                service_fee=self.service_fee_var.get().strip() or None,
                payment_status=self.acct_payment_status.get() or None,
                sla=self.sla_var.get().strip() or None,
                headcount=int(self.headcount_var.get().strip()) if self.headcount_var.get().strip().isdigit() else None,
            )
        except Exception as exc:
            self.feedback.error(f"Could not save tax IDs: {exc}")
            return
        self.feedback.success("Tax IDs & service info saved.")
        self.refresh()

    def _build_filing_statuses(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)

        # Title row
        title_row = ctk.CTkFrame(frame, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            title_row,
            text="Tax Filing Statuses",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        self.filing_last_changed_label = ctk.CTkLabel(
            title_row, text="", text_color=TEXT_FAINT,
            font=ctk.CTkFont(size=11),
        )
        self.filing_last_changed_label.grid(row=0, column=1, sticky="e")

        # Progress summary bar
        summary_frame = ctk.CTkFrame(frame, fg_color="transparent")
        summary_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.filing_summary_labels: dict[str, ctk.CTkLabel] = {}
        for idx, (key, color) in enumerate([
            ("complete", "#16a34a"), ("ongoing", "#ca8a04"),
            ("pending", "#dc2626"), ("na", "#6b7280"),
        ]):
            lbl = ctk.CTkLabel(
                summary_frame, text="0", font=ctk.CTkFont(size=20, weight="bold"),
                text_color=color,
            )
            lbl.grid(row=0, column=idx, sticky="w", padx=(0 if idx == 0 else 16, 0))
            ctk.CTkLabel(
                summary_frame,
                text=["Complete", "On-Going", "Pending", "N/A"][idx],
                text_color=TEXT_MUTED, font=ctk.CTkFont(size=11),
            ).grid(row=1, column=idx, sticky="w", padx=(0 if idx == 0 else 16, 0))
            self.filing_summary_labels[key] = lbl

        # Filing status rows
        self.filing_vars: dict[str, ctk.StringVar] = {}
        self.filing_labels: dict[str, ctk.CTkLabel] = {}
        self.filing_delete_btns: dict[str, ctk.CTkButton] = {}

        for idx, field in enumerate(TAX_FILING_FIELDS):
            row = idx + 2
            ctk.CTkLabel(
                frame, text=TAX_FILING_LABELS[field],
                font=ctk.CTkFont(size=13),
            ).grid(row=row, column=0, sticky="w", padx=16, pady=(4, 2))

            var = ctk.StringVar(value="Not Applicable")
            self.filing_vars[field] = var
            var.trace_add("write", lambda *_a, f=field: self._on_filing_status_change(f))
            menu = ctk.CTkOptionMenu(frame, values=list(TAX_FILING_STATUSES), variable=var)
            menu.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=(4, 2))

            lbl = ctk.CTkLabel(frame, text="\u2b1c", font=ctk.CTkFont(size=18))
            lbl.grid(row=row, column=2, padx=(0, 4), pady=(4, 2))
            self.filing_labels[field] = lbl

            edit_btn = ctk.CTkButton(
                frame, text="Edit", width=50, height=28,
                font=ctk.CTkFont(size=11),
                command=lambda f=field: self._edit_filing_status(f),
            )
            edit_btn.grid(row=row, column=3, padx=(0, 4), pady=(4, 2))

            del_btn = ctk.CTkButton(
                frame, text="\u2716", width=28, height=28,
                font=ctk.CTkFont(size=12),
                fg_color=("gray70", "gray30"),
                hover_color=("#dc2626", "#b91c1c"),
                command=lambda f=field: self._reset_filing_status(f),
            )
            del_btn.grid(row=row, column=4, padx=(0, 16), pady=(4, 2))
            self.filing_delete_btns[field] = del_btn

        # Save + Reset All buttons
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=len(TAX_FILING_FIELDS) + 2, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8))
        ctk.CTkLabel(
            btn_row,
            text="Changes save automatically when you pick a status.",
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            btn_row, text="Reset All to N/A", width=140,
            fg_color=("#dc2626", "#b91c1c"),
            hover_color=("#b91c1c", "#991b1b"),
            command=self._reset_all_filing_statuses,
        ).pack(side="left")

        # Change history section
        history_frame = ctk.CTkFrame(frame, fg_color="transparent")
        history_frame.grid(
            row=len(TAX_FILING_FIELDS) + 3, column=0, sticky="ew", padx=16, pady=(0, 14)
        )
        history_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            history_frame,
            text="Recent Changes",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        from skyadmin_pro.ui.widgets import ThemedTreeview
        self.filing_history_tree = ThemedTreeview(
            history_frame,
            columns=(
                ("date", "Date", 140),
                ("field", "Filing", 130),
                ("old", "From", 120),
                ("new", "To", 120),
            ),
        )
        self.filing_history_tree.tree.configure(height=5)
        self.filing_history_tree.grid(row=1, column=0, sticky="ew")

        return frame

    def _on_filing_status_change(self, field: str) -> None:
        if self._filing_suspend_save:
            return
        self._persist_filing_field(field)

    def _persist_filing_field(self, field: str) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            return
        old = self.app.db.get_client_tax_summary(client_id)
        new_val = self.filing_vars[field].get()
        if old.get(field) == new_val:
            return
        client = self.app.db.get_client(client_id)
        client_name = (client or {}).get("name") or "client"
        self.app.db.log_tax_change(client_id, field, old.get(field), new_val)
        if new_val in ("Pending", "On-Going"):
            label = TAX_FILING_LABELS.get(field, field)
            self.app.db.add_task(
                title=f"Tax filing: {label} — {client_name}",
                client_id=client_id,
                category="General",
                description=f"Status changed from {old.get(field, 'N/A')} to {new_val}.",
            )
        self.app.db.update_client_fields(client_id, **{field: new_val})
        val = new_val if new_val in TAX_FILING_STATUSES else "Not Applicable"
        self.filing_labels[field].configure(
            text="\u2705" if val == "Complete"
            else "\U0001f7e1" if val == "On-Going"
            else "\u274c" if val == "Pending"
            else "\u2b1c"
        )
        last_changed = self.app.db.get_filing_last_changed(client_id)
        self.filing_last_changed_label.configure(
            text=f"Last changed: {last_changed}" if last_changed else ""
        )
        history = self.app.db.get_filing_change_history(client_id, limit=20)
        self.filing_history_tree.set_rows(
            [
                (
                    row.get("changed_at") or "",
                    TAX_FILING_LABELS.get(row.get("field") or "", row.get("field") or ""),
                    row.get("old_value") or "",
                    row.get("new_value") or "",
                )
                for row in history
            ]
        )
        self.feedback.success(f"{TAX_FILING_LABELS.get(field, field)} saved.")

    def _save_filing_statuses(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        for field in TAX_FILING_FIELDS:
            self._persist_filing_field(field)
        self.feedback.success("All filing statuses saved.")
        self.refresh()

    def _edit_filing_status(self, field: str) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        label = TAX_FILING_LABELS.get(field, field)
        current = self.filing_vars[field].get()
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Edit {label}")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.transient(self.winfo_toplevel())
        make_modal(dialog)
        ctk.CTkLabel(dialog, text=f"Status for {label}:").grid(
            row=0, column=0, padx=16, pady=(12, 4), sticky="w"
        )
        status_var = ctk.StringVar(value=current)
        ctk.CTkOptionMenu(
            dialog, values=list(TAX_FILING_STATUSES), variable=status_var, width=200,
        ).grid(row=0, column=1, padx=(0, 16), pady=(12, 4), sticky="ew")

        def _confirm() -> None:
            new_val = status_var.get()
            old_val = self.filing_vars[field].get()
            if new_val != old_val:
                self.app.db.log_tax_change(client_id, field, old_val, new_val)
                self.app.db.update_client_fields(client_id, **{field: new_val})
                if new_val in ("Pending", "On-Going"):
                    client = self.app.db.get_client(client_id)
                    client_name = (client or {}).get("name") or "client"
                    self.app.db.add_task(
                        title=f"Tax filing: {label} — {client_name}",
                        client_id=client_id,
                        category="General",
                        description=f"Status changed from {old_val} to {new_val}.",
                    )
            dialog.destroy()
            self.feedback.success(f"{label} updated to {new_val}.")
            self.refresh()

        ctk.CTkButton(dialog, text="Save", width=100, command=_confirm).grid(
            row=1, column=0, columnspan=2, pady=(12, 16)
        )

    def _reset_filing_status(self, field: str) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        label = TAX_FILING_LABELS.get(field, field)
        old_val = self.filing_vars[field].get()
        if old_val == "Not Applicable":
            return
        self.app.db.log_tax_change(client_id, field, old_val, "Not Applicable")
        self.app.db.update_client_fields(client_id, **{field: "Not Applicable"})
        self.feedback.success(f"{label} reset to N/A.")
        self.refresh()

    def _reset_all_filing_statuses(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        updates = {}
        for field in TAX_FILING_FIELDS:
            old_val = self.filing_vars[field].get()
            if old_val != "Not Applicable":
                self.app.db.log_tax_change(client_id, field, old_val, "Not Applicable")
                updates[field] = "Not Applicable"
        if updates:
            self.app.db.update_client_fields(client_id, **updates)
            self.feedback.success(f"{len(updates)} filing status(es) reset to N/A.")
        else:
            self.feedback.info("All filing statuses already N/A.")
        self.refresh()

    def _build_vo_csh_setup(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        self._vo_csh_setup_rows: dict[str, dict] = {}
        self._selected_vo_csh_setup_id: int | None = None

        ctk.CTkLabel(
            frame,
            text="VO / CSH renewal rollout",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            frame,
            text=(
                "Clients with Virtual Office or CSH rental documents. Infer renewal dates "
                "from document expiry, then review providers and addresses on the VO & CSH tab."
            ),
            wraplength=760,
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        ctk.CTkLabel(toolbar, text="Show", anchor="w").grid(row=0, column=0, padx=(0, 8))
        self.vo_csh_setup_filter = ctk.CTkOptionMenu(
            toolbar,
            values=["All", "Needs setup", "Ready"],
            command=lambda _c: self.refresh_vo_csh_setup(),
            width=140,
        )
        self.vo_csh_setup_filter.set("All")
        self.vo_csh_setup_filter.grid(row=0, column=1, sticky="w")
        self.vo_csh_setup_summary = ctk.CTkLabel(
            toolbar, text="", text_color=TEXT_MUTED, anchor="w"
        )
        self.vo_csh_setup_summary.grid(row=0, column=2, sticky="ew", padx=(16, 0))
        toolbar.grid_columnconfigure(2, weight=1)

        self.vo_csh_setup_tree = ThemedTreeview(
            frame,
            columns=(
                ("company", "Company", 200),
                ("status", "Setup", 80),
                ("vo_docs", "VO docs", 70),
                ("vo_date", "VO renewal", 100),
                ("vo_suggest", "Suggested VO", 100),
                ("csh_docs", "CSH docs", 70),
                ("csh_date", "CSH renewal", 100),
                ("csh_suggest", "Suggested CSH", 100),
            ),
            on_select=self._on_vo_csh_setup_select,
            on_double_click=self._open_selected_vo_csh_tab,
            showheight=10,
        )
        self.vo_csh_setup_tree.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 14))
        ctk.CTkButton(
            actions,
            text="Open VO & CSH",
            width=130,
            command=self._open_selected_vo_csh_tab,
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Infer renewal dates",
            width=150,
            command=self._infer_selected_vo_csh_dates,
        ).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Infer all missing",
            width=130,
            fg_color="transparent",
            border_width=1,
            command=self._infer_all_vo_csh_dates,
        ).grid(row=0, column=2)
        return frame

    def refresh_vo_csh_setup(self) -> None:
        if not hasattr(self, "vo_csh_setup_tree"):
            return
        self.vo_csh_setup_tree.apply_theme()
        rows = list_vo_csh_setup_rows(self.app.db)
        ready = sum(1 for row in rows if not row.get("setup_missing"))
        self.vo_csh_setup_summary.configure(
            text=f"{ready} of {len(rows)} VO/CSH client(s) have renewal dates set"
        )
        filt = self.vo_csh_setup_filter.get()
        if filt == "Needs setup":
            rows = [row for row in rows if row.get("setup_missing")]
        elif filt == "Ready":
            rows = [row for row in rows if not row.get("setup_missing")]

        self._vo_csh_setup_rows = {}
        tree_rows = []
        iids = []
        tags = []
        for row in rows:
            iid = str(row["id"])
            self._vo_csh_setup_rows[iid] = row
            iids.append(iid)
            tree_rows.append(
                (
                    row.get("name") or "",
                    row.get("setup_status") or "",
                    str(int(row.get("vo_doc_count") or 0)),
                    row.get("vo_renewal_date") or "—",
                    row.get("suggested_vo_renewal_date") or "—",
                    str(int(row.get("csh_doc_count") or 0)),
                    row.get("csh_renewal_date") or "—",
                    row.get("suggested_csh_renewal_date") or "—",
                )
            )
            status = row.get("setup_status")
            if status == "Ready":
                tags.append(("done",))
            elif status == "Almost":
                tags.append(("watch",))
            else:
                tags.append(("urgent",))
        self.vo_csh_setup_tree.set_rows(tree_rows, iids=iids, tags=tags)

    def _on_vo_csh_setup_select(self, iid: str | None) -> None:
        self._selected_vo_csh_setup_id = int(iid) if iid else None

    def _selected_vo_csh_setup_row(self) -> dict | None:
        if self._selected_vo_csh_setup_id is None:
            return None
        return self._vo_csh_setup_rows.get(str(self._selected_vo_csh_setup_id))

    def _open_selected_vo_csh_tab(self, _iid: str | None = None) -> None:
        row = self._selected_vo_csh_setup_row()
        if not row:
            self.feedback.error("Select a client first.")
            return
        self.select_client((row.get("name") or "").strip())
        self.tabs.set("VO & CSH")
        self.refresh()

    def _infer_selected_vo_csh_dates(self) -> None:
        row = self._selected_vo_csh_setup_row()
        if not row:
            self.feedback.error("Select a client first.")
            return
        if not row.get("can_infer_vo") and not row.get("can_infer_csh"):
            self.feedback.error("No document expiry dates available to infer.")
            return
        result = infer_client_vo_csh_renewal_dates(self.app.db, int(row["id"]))
        total = int(result["vo"]) + int(result["csh"])
        if not total:
            self.feedback.info("Nothing to infer for this client.")
            return
        self.feedback.success(
            f"Inferred {result['vo']} VO and {result['csh']} CSH renewal date(s)."
        )
        self.refresh_vo_csh_setup()
        self.refresh()

    def _infer_all_vo_csh_dates(self) -> None:
        pending = sum(
            1
            for row in list_vo_csh_setup_rows(self.app.db)
            if row.get("can_infer_vo") or row.get("can_infer_csh")
        )
        if pending == 0:
            self.feedback.info("No clients need renewal date inference.")
            return
        if not messagebox.askyesno(
            "Infer VO/CSH renewal dates",
            f"Infer renewal dates from document expiry for {pending} client(s)?",
            parent=self.winfo_toplevel(),
        ):
            return
        result = infer_vo_csh_renewal_dates(self.app.db, only_missing=True)
        total = int(result["vo"]) + int(result["csh"])
        self.feedback.success(
            f"Inferred {result['vo']} VO and {result['csh']} CSH renewal date(s) "
            f"({total} total)."
        )
        self.refresh_vo_csh_setup()
        self.refresh()

    def _build_vo_csh(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Virtual Office & Company Seal Holder",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure((0, 1), weight=1)

        self.vo_address_var = ctk.StringVar()
        self.vo_provider_var = ctk.StringVar()
        self.vo_renewal_var = ctk.StringVar()
        self.csh_provider_var = ctk.StringVar()
        self.csh_renewal_var = ctk.StringVar()
        self.shareholder_var = ctk.StringVar()

        ctk.CTkLabel(form, text="VO Address").grid(row=0, column=0, sticky="w", pady=(2, 2))
        ctk.CTkEntry(form, textvariable=self.vo_address_var).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )
        ctk.CTkLabel(form, text="VO Service Provider").grid(
            row=2, column=0, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(form, textvariable=self.vo_provider_var).grid(
            row=3, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="VO Renewal Date").grid(
            row=2, column=1, sticky="w", pady=(6, 2)
        )
        DatePickerField(form, var=self.vo_renewal_var).grid(
            row=3, column=1, sticky="ew", pady=(0, 4)
        )

        ctk.CTkLabel(form, text="CSH Service Provider").grid(
            row=4, column=0, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(form, textvariable=self.csh_provider_var).grid(
            row=5, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="CSH Renewal Date").grid(
            row=4, column=1, sticky="w", pady=(6, 2)
        )
        DatePickerField(form, var=self.csh_renewal_var).grid(
            row=5, column=1, sticky="ew", pady=(0, 4)
        )

        ctk.CTkLabel(form, text="Shareholders (e.g. Thai 51%, Foreign 49%)").grid(
            row=6, column=0, sticky="w", pady=(6, 2)
        )
        ctk.CTkEntry(form, textvariable=self.shareholder_var).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )

        ctk.CTkButton(
            frame, text="Save VO & CSH", width=160,
            command=self._save_vo_csh,
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(8, 14))
        return frame

    def _save_vo_csh(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        old = self.app.db.get_client(client_id) or {}
        new_vo_date = None
        vo_raw = self.vo_renewal_var.get().strip()
        if vo_raw:
            new_vo_date = parse_flexible_date(vo_raw)
            if not new_vo_date:
                self.feedback.error("VO renewal date is not a valid date (e.g. 2026-08-25).")
                return
        new_csh_date = None
        csh_raw = self.csh_renewal_var.get().strip()
        if csh_raw:
            new_csh_date = parse_flexible_date(csh_raw)
            if not new_csh_date:
                self.feedback.error("CSH renewal date is not a valid date (e.g. 2026-08-25).")
                return
        old_vo_date = old.get("vo_renewal_date") or None
        old_csh_date = old.get("csh_renewal_date") or None
        try:
            self.app.db.update_client_fields(
                client_id,
                vo_address=self.vo_address_var.get().strip() or None,
                vo_service_provider=self.vo_provider_var.get().strip() or None,
                vo_renewal_date=new_vo_date,
                csh_service_provider=self.csh_provider_var.get().strip() or None,
                csh_renewal_date=new_csh_date,
                shareholder_info=self.shareholder_var.get().strip() or None,
            )
            # VO renewal integration
            if new_vo_date and new_vo_date != old_vo_date:
                self.app.db.create_vo_csh_renewal(client_id, "vo", new_vo_date)
            elif not new_vo_date and old_vo_date:
                self.app.db.delete_vo_csh_renewal(client_id, "vo")
            # CSH renewal integration
            if new_csh_date and new_csh_date != old_csh_date:
                self.app.db.create_vo_csh_renewal(client_id, "csh", new_csh_date)
            elif not new_csh_date and old_csh_date:
                self.app.db.delete_vo_csh_renewal(client_id, "csh")
        except Exception as exc:
            self.feedback.error(f"Could not save VO & CSH: {exc}")
            return
        self.feedback.success("VO & CSH info saved.")
        self.refresh()

    def _build_financial_docs(self, master) -> ctk.CTkFrame:
        from skyadmin_pro.config import FINANCIAL_DOC_CATEGORIES, FINANCIAL_DOC_SUBCATEGORIES
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Financial Documents",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        # Summary label
        self.fin_summary_label = ctk.CTkLabel(
            frame, text="", text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        )
        self.fin_summary_label.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 4))

        # Filter row
        filter_row = ctk.CTkFrame(frame, fg_color="transparent")
        filter_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        filter_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(filter_row, text="Category:").grid(row=0, column=0, padx=(0, 8))
        self.fin_category_filter = ctk.CTkOptionMenu(
            filter_row, values=["All"] + list(FINANCIAL_DOC_CATEGORIES),
            command=lambda _: self._refresh_financial_docs(),
        )
        self.fin_category_filter.grid(row=0, column=1, sticky="w")
        self.fin_category_filter.set("All")

        # Treeview
        from skyadmin_pro.ui.widgets import ThemedTreeview
        self.fin_doc_tree = ThemedTreeview(
            frame,
            columns=(
                ("date", "Date", 90),
                ("category", "Category", 110),
                ("subcategory", "From", 90),
                ("file", "File Name", 200),
                ("amount", "Amount", 100),
                ("desc", "Description", 180),
            ),
        )
        self.fin_doc_tree.tree.configure(height=8)
        self.fin_doc_tree.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Buttons
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        btn_row.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(
            btn_row, text="Add Document", width=120,
            command=self._add_financial_doc,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            btn_row, text="Open File", width=100,
            fg_color="transparent", border_width=1,
            command=self._open_financial_doc,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkButton(
            btn_row, text="Delete", width=80,
            fg_color="transparent", border_width=1,
            text_color="#dc2626",
            command=self._delete_financial_doc,
        ).grid(row=0, column=2, sticky="w", padx=(8, 0))

        return frame

    def _refresh_financial_docs(self) -> None:
        client_id = self._selected_client_id()
        self.fin_doc_tree.apply_theme()
        if client_id is None:
            self.fin_doc_tree.set_rows([])
            self.fin_summary_label.configure(text="")
            return
        cat_filter = self.fin_category_filter.get()
        category = None if cat_filter == "All" else cat_filter
        docs = self.app.db.list_financial_documents(client_id, category)
        summary = self.app.db.financial_doc_summary(client_id)
        total = sum(summary.values())
        parts = [f"{cat}: {n}" for cat, n in sorted(summary.items())]
        self.fin_summary_label.configure(
            text=f"{total} document(s)" + (f" — {', '.join(parts)}" if parts else "")
        )
        rows, iids = [], []
        for d in docs:
            rows.append((
                d.get("doc_date") or "—",
                d.get("category") or "—",
                d.get("subcategory") or "—",
                d.get("file_name") or "—",
                d.get("amount") or "—",
                d.get("description") or "—",
            ))
            iids.append(str(d["id"]))
        self.fin_doc_tree.set_rows(rows, iids=iids)

    def _add_financial_doc(self) -> None:
        from tkinter import filedialog
        from skyadmin_pro.config import FINANCIAL_DOC_CATEGORIES, FINANCIAL_DOC_SUBCATEGORIES, FINANCIAL_DOC_FOLDER_MAP
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        file_path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Select financial document",
            filetypes=[
                ("All supported", "*.pdf *.jpg *.jpeg *.png *.xlsx *.xls *.csv"),
                ("PDF files", "*.pdf"),
                ("Images", "*.jpg *.jpeg *.png"),
                ("Excel", "*.xlsx *.xls *.csv"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return
        import os
        from pathlib import Path
        file_name = os.path.basename(file_path)
        # Build category selection dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Document Details")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.transient(self.winfo_toplevel())
        make_modal(dialog)
        ctk.CTkLabel(dialog, text="Category:").grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")
        cat_var = ctk.StringVar(value=FINANCIAL_DOC_CATEGORIES[0])
        ctk.CTkOptionMenu(dialog, values=list(FINANCIAL_DOC_CATEGORIES), variable=cat_var).grid(
            row=0, column=1, padx=(0, 16), pady=(12, 4), sticky="ew"
        )
        ctk.CTkLabel(dialog, text="From:").grid(row=1, column=0, padx=16, pady=(4, 4), sticky="w")
        sub_var = ctk.StringVar(value=FINANCIAL_DOC_SUBCATEGORIES[0])
        ctk.CTkOptionMenu(dialog, values=list(FINANCIAL_DOC_SUBCATEGORIES), variable=sub_var).grid(
            row=1, column=1, padx=(0, 16), pady=(4, 4), sticky="ew"
        )
        ctk.CTkLabel(dialog, text="Amount:").grid(row=2, column=0, padx=16, pady=(4, 4), sticky="w")
        amt_var = ctk.StringVar()
        ctk.CTkEntry(dialog, textvariable=amt_var, width=200).grid(
            row=2, column=1, padx=(0, 16), pady=(4, 4), sticky="ew"
        )
        ctk.CTkLabel(dialog, text="Date:").grid(row=3, column=0, padx=16, pady=(4, 4), sticky="w")
        date_var = ctk.StringVar(value=date.today().isoformat())
        DatePickerField(dialog, var=date_var).grid(
            row=3, column=1, padx=(0, 16), pady=(4, 4), sticky="ew"
        )
        ctk.CTkLabel(dialog, text="Description:").grid(row=4, column=0, padx=16, pady=(4, 4), sticky="w")
        desc_var = ctk.StringVar()
        ctk.CTkEntry(dialog, textvariable=desc_var, width=200).grid(
            row=4, column=1, padx=(0, 16), pady=(4, 4), sticky="ew"
        )

        def _confirm() -> None:
            category = cat_var.get()
            subcategory = sub_var.get()
            # Copy file to workspace
            client = self.app.db.get_client(client_id)
            client_name = (client or {}).get("name") or "client"
            folder_name = FINANCIAL_DOC_FOLDER_MAP.get(category, "General_Expenses")
            try:
                client_folder = resolve_client_folder(
                    self.app.paths.clients, client_name, create=True
                )
            except Exception as exc:
                self.feedback.error(str(exc))
                return
            dest_dir = client_folder / "04_Financial_Docs" / folder_name
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self.feedback.error(f"Cannot create document folder: {exc}")
                return
            dest_path = dest_dir / file_name
            # Prevent duplicate file copies — add numeric suffix if exists
            if dest_path.exists():
                stem = dest_path.stem
                suffix = dest_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            try:
                import shutil
                shutil.copy2(file_path, dest_path)
                stored = str(dest_path)
            except Exception:
                stored = ""
            self.app.db.add_financial_document(
                client_id=client_id,
                category=category,
                subcategory=subcategory,
                file_name=dest_path.name,
                file_path=file_path,
                stored_path=stored,
                amount=amt_var.get().strip(),
                doc_date=date_var.get().strip(),
                description=desc_var.get().strip(),
            )
            dialog.destroy()
            self.feedback.success(f"Document '{dest_path.name}' added.")
            self._refresh_financial_docs()

        ctk.CTkButton(
            dialog, text="Add", width=100, command=_confirm,
        ).grid(row=5, column=0, columnspan=2, pady=(12, 16))

    def _open_financial_doc(self) -> None:
        from skyadmin_pro.services.file_ops import open_in_file_manager
        selected = self.fin_doc_tree.tree.selection()
        if not selected:
            self.feedback.error("Select a document first.")
            return
        doc_id = int(selected[0])
        doc = self.app.db.get_financial_document(doc_id)
        if not doc:
            return
        path = doc.get("stored_path") or doc.get("file_path") or ""
        if not path or not os.path.exists(path):
            self.feedback.error("File not found on disk.")
            return
        try:
            open_in_file_manager(Path(path))
        except (OSError, RuntimeError) as exc:
            self.feedback.error(f"Could not open file: {exc}")

    def _delete_financial_doc(self) -> None:
        selected = self.fin_doc_tree.tree.selection()
        if not selected:
            self.feedback.error("Select a document first.")
            return
        import tkinter.messagebox as mb
        if not mb.askyesno(
            "Delete", "Delete this financial document?",
            parent=self.winfo_toplevel(),
        ):
            return
        doc_id = int(selected[0])
        doc = self.app.db.delete_financial_document(doc_id)
        if doc:
            stored = doc.get("stored_path") or ""
            if stored and os.path.exists(stored):
                try:
                    os.remove(stored)
                except OSError:
                    pass
        self.feedback.success("Document deleted.")
        self._refresh_financial_docs()

    def _selected_client_id(self) -> int | None:
        name = self.company_box.get().strip()
        if not name:
            return None
        # Lookup only — never create a client as a side effect of reading.
        return self.app.db.client_id_by_name(name)

    def select_client(self, name: str) -> None:
        self._fill_combo(name)

    def _fill_combo(self, current: str) -> None:
        names = self.app.db.list_client_names()
        _fill_combo(self.company_box, names, current)

    def _on_company(self, _choice: str) -> None:
        self._editing_service_id = None
        self._editing_doc_id = None
        self.refresh()

    def refresh(self) -> None:
        self._fill_combo(self.company_box.get())
        client_id = self._selected_client_id()

        self.service_tree.apply_theme()
        self.doc_tree.apply_theme()

        if client_id is None:
            self.company_info.configure(text="Select a company to see services and documents.")
            self.company_name_label.configure(text="—")
            self.service_tree.set_rows([])
            self.doc_tree.set_rows([])
            for var in (self.info_reg_number, self.info_director, self.info_email,
                        self.info_contact, self.info_capital, self.info_vat, self.info_address):
                var.set("")
            self.info_objectives.delete("1.0", "end")
            self.tax_id_var.set("")
            self._load_client_credentials_display(None)
            self.vat_registered_var.set(False)
            self.vat_reg_date_var.set("")
            self.acct_service_type.set("")
            self.acct_txn_volume.set("")
            self.service_fee_var.set("")
            self.acct_payment_status.set("")
            self.sla_var.set("")
            self.headcount_var.set("")
            for field in TAX_FILING_FIELDS:
                if field in self.filing_vars:
                    self.filing_vars[field].set("Not Applicable")
            for key, lbl in self.filing_summary_labels.items():
                lbl.configure(text="0")
            self.refresh_accounting_setup()
            self.refresh_vo_csh_setup()
            return

        services = self.app.db.list_client_services(client_id)
        documents = self.app.db.list_client_documents(client_id)
        self.company_info.configure(
            text=f"{len(services)} service(s) \u00b7 {len(documents)} document(s)"
        )

        client = self.app.db.get_client(client_id)
        self.company_name_label.configure(text=client["name"] if client else "\u2014")
        self.info_reg_number.set((client or {}).get("registration_number") or "")
        self.info_director.set((client or {}).get("director") or "")
        self.info_email.set((client or {}).get("email") or "")
        self.info_contact.set((client or {}).get("contact_number") or "")
        self.info_capital.set((client or {}).get("registered_capital") or "")
        self.info_vat.set((client or {}).get("vat_registration") or "")
        self.info_address.set((client or {}).get("business_address") or "")
        self.info_objectives.delete("1.0", "end")
        self.info_objectives.insert("1.0", (client or {}).get("business_objectives") or "")

        # Tax IDs sub-tab
        self.tax_id_var.set((client or {}).get("tax_id") or "")
        self._load_client_credentials_display(client_id)
        self.vat_registered_var.set(bool((client or {}).get("vat_registered")))
        self.vat_reg_date_var.set((client or {}).get("vat_registered_date") or "")
        self.acct_service_type.set((client or {}).get("service_type") or "")
        acct_txn = (client or {}).get("num_transactions") or ""
        if acct_txn in TRANSACTION_RANGES:
            self.acct_txn_volume.set(acct_txn)
        else:
            self.acct_txn_volume.set(TRANSACTION_RANGES[0] if TRANSACTION_RANGES else "")
        self.service_fee_var.set((client or {}).get("service_fee") or "")
        self.acct_payment_status.set((client or {}).get("payment_status") or "N/A")
        self.sla_var.set((client or {}).get("sla") or "")
        hc = (client or {}).get("headcount")
        self.headcount_var.set(str(hc) if hc is not None else "")

        # Filing Statuses sub-tab
        counts = {"complete": 0, "ongoing": 0, "pending": 0, "na": 0}
        self._filing_suspend_save = True
        try:
            for field in TAX_FILING_FIELDS:
                val = (client or {}).get(field) or "Not Applicable"
                if val not in TAX_FILING_STATUSES:
                    val = "Not Applicable"
                self.filing_vars[field].set(val)
                self.filing_labels[field].configure(
                    text="\u2705" if val == "Complete"
                    else "\U0001f7e1" if val == "On-Going"
                    else "\u274c" if val == "Pending"
                    else "\u2b1c"
                )
                if val == "Complete":
                    counts["complete"] += 1
                elif val == "On-Going":
                    counts["ongoing"] += 1
                elif val == "Pending":
                    counts["pending"] += 1
                else:
                    counts["na"] += 1
        finally:
            self._filing_suspend_save = False
        for key, lbl in self.filing_summary_labels.items():
            lbl.configure(text=str(counts[key]))
        # Last changed timestamp
        last_changed = self.app.db.get_filing_last_changed(client_id) if client_id else None
        self.filing_last_changed_label.configure(
            text=f"Last changed: {last_changed}" if last_changed else ""
        )
        # Filing change history
        self.filing_history_tree.apply_theme()
        history = self.app.db.get_filing_change_history(client_id) if client_id else []
        hist_rows, hist_iids = [], []
        for h in history:
            hist_rows.append((
                h.get("changed_at") or "",
                TAX_FILING_LABELS.get(h.get("field") or "", h.get("field") or ""),
                h.get("old_value") or "—",
                h.get("new_value") or "—",
            ))
            hist_iids.append(str(h["id"]))
        self.filing_history_tree.set_rows(hist_rows, iids=hist_iids)

        # VO & CSH sub-tab
        self.vo_address_var.set((client or {}).get("vo_address") or "")
        self.vo_provider_var.set((client or {}).get("vo_service_provider") or "")
        self.vo_renewal_var.set((client or {}).get("vo_renewal_date") or "")
        self.csh_provider_var.set((client or {}).get("csh_service_provider") or "")
        self.csh_renewal_var.set((client or {}).get("csh_renewal_date") or "")
        self.shareholder_var.set((client or {}).get("shareholder_info") or "")

        # Financial Docs sub-tab
        self._refresh_financial_docs()

        # Services treeview
        rows, iids, tags = [], [], []
        for item in services:
            progress = item.get("progress") or "Not started"
            row_tags = []
            if progress == "Completed":
                row_tags.append("done")
            elif progress == "Ongoing":
                row_tags.append("wip")
            expiry = item.get("expiry_date")
            eff = effective_expiry_date(expiry, item.get("document_type"))
            left = days_until(eff) if eff else None
            if left is not None:
                tag = classify_expiry(left)
                if tag:
                    row_tags.append(tag)
            rows.append(
                (
                    item.get("document_type") or "\u2014",
                    item.get("start_date") or "\u2014",
                    eff or "\u2014",
                    item.get("payment_date") or "\u2014",
                    format_thousands(item.get("amount")) if item.get("amount") else "\u2014",
                    progress,
                    "Yes" if item.get("paid") else "\u2014",
                )
            )
            iids.append(str(item["id"]))
            tags.append(tuple(row_tags))
        self.service_tree.set_rows(rows, iids=iids, tags=tags)

        # Documents treeview
        rows, iids, tags = [], [], []
        for item in documents:
            expiry = item.get("expiry_date")
            eff = effective_expiry_date(expiry, item.get("document_type"))
            left = days_until(eff) if eff else None
            row_tags = []
            if left is not None:
                tag = classify_expiry(left)
                if tag:
                    row_tags.append(tag)
            rows.append(
                (
                    item.get("document_type") or "\u2014",
                    item.get("file_name") or "\u2014",
                    eff or "\u2014",
                    (item.get("created_at") or "")[:10],
                )
            )
            iids.append(str(item["id"]))
            tags.append(tuple(row_tags))
        self.doc_tree.set_rows(rows, iids=iids, tags=tags)
        self.refresh_accounting_setup()
        self.refresh_vo_csh_setup()

    def _parse_date(self, var: ctk.StringVar) -> str | None:
        raw = var.get().strip()
        if not raw:
            return None
        parsed = parse_flexible_date(raw)
        if not parsed:
            raise ValueError("Enter a valid date (YYYY-MM-DD or DD/MM/YYYY).")
        return parsed

    def _edit_service(self, iid: str | None) -> None:
        if iid is None:
            return
        item = self.app.db.get_document(int(iid))
        if not item:
            return
        self._editing_service_id = int(item["id"])
        self.service_status_label.configure(text="Editing service record — Save to update")
        if item.get("document_type") in self.app.db.list_service_types():
            self.service_type.set(item["document_type"])
        self.service_start.set(item.get("start_date") or "")
        self.service_expiry.set(item.get("expiry_date") or "")
        self.service_payment.set(item.get("payment_date") or "")
        self.service_amount.set(item.get("amount") or "")
        progress = item.get("progress") or "Not started"
        if progress not in SERVICE_PROGRESS:
            progress = "Not started"
        self.service_progress.set(progress)
        if item.get("paid"):
            self.service_paid.select()
        else:
            self.service_paid.deselect()

    def _edit_document(self, iid: str | None) -> None:
        if iid is None:
            return
        item = self.app.db.get_document(int(iid))
        if not item:
            return
        self._editing_doc_id = int(item["id"])
        self.document_status_label.configure(text="Editing document record — Save to update")
        if item.get("document_type") in IMPORTANT_DOC_TYPES:
            self.doc_type.set(item["document_type"])
        self.doc_expiry.set(item.get("expiry_date") or "")
        self.doc_file.set(item.get("file_name") or "")
        self.doc_path.set("")

    def _pick_document_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Pick document file",
            filetypes=[
                ("All files", "*.*"),
                ("PDF files", "*.pdf"),
                ("Images", "*.png *.jpg *.jpeg *.tif *.tiff"),
            ],
        )
        if path:
            self.doc_path.set(path)
            self.doc_file.set(Path(path).name)

    def _save_service(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        try:
            start = self._parse_date(self.service_start)
            expiry = self._parse_date(self.service_expiry)
            payment = self._parse_date(self.service_payment)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        progress = self.service_progress.get()
        raw_amount = self.service_amount.get().strip()
        amount = sanitize_amount(raw_amount) if raw_amount else None
        paid = bool(self.service_paid.get())
        if self._editing_service_id is None:
            self.app.db.record_document(
                client_id=client_id,
                document_type=self.service_type.get(),
                file_name="",
                file_path="",
                expiry_date=expiry,
                payment_date=payment,
                start_date=start,
                amount=amount,
                progress=progress,
                paid=paid,
            )
            self.feedback.success("Service record saved.")
        else:
            self.app.db.update_document(
                self._editing_service_id,
                document_type=self.service_type.get(),
                expiry_date=expiry,
                payment_date=payment,
                start_date=start,
                amount=amount,
                progress=progress,
                paid=paid,
                clear=True,
            )
            self.feedback.success("Service record updated.")
        self._editing_service_id = None
        self.service_status_label.configure(text="New service record")
        self.service_start.set("")
        self.service_expiry.set("")
        self.service_payment.set("")
        self.service_amount.set("")
        self.service_progress.set(SERVICE_PROGRESS[0])
        self.service_paid.deselect()
        self.refresh()

    def _renew_service(self) -> None:
        iid = self.service_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a service to renew.")
            return
        service = self.app.db.get_document(int(iid))
        if not service:
            self.feedback.error("Service record not found.")
            return
        top = ctk.CTkToplevel(self)
        top.title("Renew / extend service")
        top.geometry("500x400")
        top.transient(self.winfo_toplevel())
        top.attributes("-topmost", True)
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text=service.get("document_type") or "Service",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            top,
            text=(
                f"Client: {service.get('client_name') or '—'}"
                f"   ·   Current expiry: {service.get('expiry_date') or '—'}"
            ),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=20)
        ctk.CTkLabel(
            top,
            text=(
                "Renew / extend before it expires — the current expiry is saved "
                "in the history before the new one is applied."
            ),
            wraplength=460,
            justify="left",
            text_color=TEXT_MUTED,
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(8, 6))

        ctk.CTkLabel(top, text="New expiry date", anchor="w").grid(
            row=3, column=0, sticky="w", padx=20, pady=(6, 2)
        )
        renew_var = ctk.StringVar()
        DatePickerField(top, var=renew_var).grid(row=4, column=0, sticky="ew", padx=20)

        ctk.CTkLabel(top, text="Note (optional)", anchor="w").grid(
            row=5, column=0, sticky="w", padx=20, pady=(8, 2)
        )
        note_var = ctk.StringVar()
        ctk.CTkEntry(top, textvariable=note_var).grid(
            row=6, column=0, sticky="ew", padx=20, pady=(0, 10)
        )

        needs_docs_var = ctk.BooleanVar(
            value=self.app.db.renewal_docs_default(
                service.get("client_id"), service.get("document_type") or ""
            )
        )
        needs_docs = ctk.CTkCheckBox(
            top,
            text="This renewal needs documents",
            variable=needs_docs_var,
        )
        needs_docs.grid(row=7, column=0, sticky="w", padx=20, pady=(0, 2))
        ctk.CTkLabel(
            top,
            text=(
                "Whether documents are needed depends on this company's task — "
                "not the service type. It can change over time, so it is editable "
                "per renewal (and in Renewal history). Your last choice for this "
                "company + service is remembered."
            ),
            wraplength=460,
            justify="left",
            text_color=TEXT_MUTED,
        ).grid(row=8, column=0, sticky="w", padx=20)

        def _do_record() -> None:
            try:
                new_expiry = self._parse_date(renew_var)
            except ValueError as exc:
                self.feedback.error(str(exc))
                return
            if new_expiry is None:
                self.feedback.error("Enter the new expiry date.")
                return
            try:
                self.app.db.record_service_renewal(
                    int(iid),
                    new_expiry,
                    note=note_var.get(),
                    needs_documents=bool(needs_docs_var.get()),
                )
            except ValueError as exc:
                self.feedback.error(str(exc))
                return
            top.destroy()
            self.feedback.success("Service renewed — expiry updated and recorded.")
            self.refresh()

        ctk.CTkButton(top, text="Record renewal", command=_do_record).grid(
            row=9, column=0, sticky="ew", padx=20, pady=(6, 18)
        )

    def _renewal_history(self) -> None:
        iid = self.service_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a service to view its renewal history.")
            return
        service = self.app.db.get_document(int(iid))
        if not service:
            self.feedback.error("Service record not found.")
            return
        renewals = self.app.db.list_service_renewals(int(iid))
        top = ctk.CTkToplevel(self)
        top.title("Renewal history")
        top.geometry("720x400")
        top.transient(self.winfo_toplevel())
        top.attributes("-topmost", True)
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            top,
            text=f"{service.get('document_type') or 'Service'} — renewal history",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        tree = ThemedTreeview(
            top,
            columns=(
                ("on", "Renewed on", 120),
                ("from", "Previous expiry", 110),
                ("to", "New expiry", 110),
                ("docs", "Documents", 100),
                ("note", "Note", 180),
            ),
        )
        tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        tree.tree.configure(height=8)

        def redraw() -> None:
            rows = self.app.db.list_service_renewals(int(iid))
            if not rows:
                tree.set_rows([("—", "No renewals recorded yet.", "", "", "")], iids=["none"])
            else:
                tree.set_rows(
                    [
                        (
                            (item["created_at"] or "")[:10],
                            item["previous_expiry"] or "—",
                            item["new_expiry"] or "—",
                            "Yes" if item.get("needs_documents") else "No",
                            item["note"] or "",
                        )
                        for item in rows
                    ],
                    iids=[str(item["id"]) for item in rows],
                )

        def _toggle_docs() -> None:
            sel = tree.selected_iid()
            if sel is None or sel == "none":
                self.feedback.error("Select a renewal row first.")
                return
            renewal = self.app.db.list_service_renewals(int(iid))
            target = next((r for r in renewal if str(r["id"]) == sel), None)
            if target is None:
                return
            self.app.db.set_renewal_needs_documents(
                int(sel), not bool(target.get("needs_documents"))
            )
            redraw()
            self.feedback.success("Document requirement updated.")

        footer = ctk.CTkFrame(top, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        ctk.CTkButton(
            footer,
            text="Toggle documents needed (selected row)",
            fg_color="transparent",
            border_width=1,
            command=_toggle_docs,
        ).pack(side="left")
        ctk.CTkLabel(
            footer,
            text=(
                "Documents needed depends on this company's task and can change "
                "over time — flip it per renewal."
            ),
            text_color=TEXT_MUTED,
        ).pack(side="right", padx=(12, 0))
        redraw()

    def _save_document(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        try:
            expiry = self._parse_date(self.doc_expiry)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        file_name = self.doc_file.get().strip()
        saved_path = None
        picked = self.doc_path.get().strip()
        if picked:
            source = Path(picked)
            if not source.is_file():
                self.feedback.error("The picked file no longer exists.")
                return
            try:
                client_name = self.company_box.get().strip()
                folder = create_client_workspace(self.app.paths.clients, client_name)
                saved = copy_file(source, folder)
            except Exception as exc:
                self.feedback.error(str(exc))
                return
            saved_path = str(saved)
            file_name = file_name or saved.name
        if self._editing_doc_id is None:
            self.app.db.record_document(
                client_id=client_id,
                document_type=self.doc_type.get(),
                file_name=file_name,
                file_path=saved_path or "",
                expiry_date=expiry,
            )
            self.feedback.success("Document record saved.")
        else:
            self.app.db.update_document(
                self._editing_doc_id,
                document_type=self.doc_type.get(),
                expiry_date=expiry,
                file_name=file_name,
                file_path=saved_path,
            )
            self.feedback.success("Document record updated.")
        self._editing_doc_id = None
        self.document_status_label.configure(text="New document record")
        self.doc_expiry.set("")
        self.doc_file.set("")
        self.doc_path.set("")
        self.refresh()

    def _delete_service(self) -> None:
        iid = self.service_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a service row first.")
            return
        if not messagebox.askyesno(
            "Delete service record", "Remove this service record?", parent=self.winfo_toplevel()
        ):
            return
        self.app.db.delete_document(int(iid))
        self.feedback.success("Service record deleted.")
        self.refresh()

    def _delete_document(self) -> None:
        iid = self.doc_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a document row first.")
            return
        if not messagebox.askyesno(
            "Delete document record", "Remove this document record?", parent=self.winfo_toplevel()
        ):
            return
        self.app.db.delete_document(int(iid))
        self.feedback.success("Document record deleted.")
        self.refresh()

    def _missing_docs_workflow(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        client = self.company_box.get().strip()
        today = date.today()
        deadline = date(today.year, today.month, 15)
        if today.day > 15:
            next_total = today.year * 12 + today.month
            deadline = date(next_total // 12, next_total % 12 + 1, 15)

        overrides = load_snippet_overrides(self.app.db.get_setting)
        template = effective_text("client", "Missing docs — initial request", overrides)
        copied = False
        if template:
            message = (
                template.replace("[Client Contact Name]", client)
                .replace("[Client Company Name]", client)
                .replace("[Month/Year]", today.strftime("%B %Y"))
                .replace("[Deadline Date]", deadline.isoformat())
            )
            try:
                copy_to_clipboard(message, tk_window=self.app)
                copied = True
            except Exception as exc:
                self.feedback.error(f"Could not copy the request email: {exc}")

        db = self.app.db
        if not messagebox.askyesno(
            "Missing docs follow-up",
            f"Create 3 follow-up tasks for {client}?\n\n"
            "• Request email (today)\n• Follow-up email (+2 days)\n• Reminder call (+3 days)",
            parent=self.winfo_toplevel(),
        ):
            return
        db.add_task(title=f"Send missing docs request to {client}", client_id=client_id, category="Accounting", due_date=today.isoformat())
        db.add_task(title=f"Follow-up: missing docs email to {client}", client_id=client_id, category="Accounting", due_date=(today + timedelta(days=2)).isoformat())
        db.add_task(title=f"Call re: missing docs for {client}", client_id=client_id, category="Accounting", due_date=(today + timedelta(days=3)).isoformat())
        self.feedback.success(
            f"3 follow-up tasks created for {client} "
            f"(today, +2d email, +3d call)."
            + (" Request email copied." if copied else "")
        )
        self.app.set_status(f"Missing-docs follow-up scheduled for {client}.")
        view = self.app._views.get("database_tasks")
        if view is not None and hasattr(view, "tasks_panel"):
            view.tasks_panel.refresh()


class RenewalPanel(ctk.CTkFrame):
    """Renewals: pick a company, then one of its renewal services, to see the
    countdown and the editable document checklist for that service's template
    (Visa / Passport / Company Setup / General — all editable in Settings)."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._checkboxes: dict[int, ctk.CTkCheckBox] = {}
        self._services: list[dict] = []
        self._service_by_value: dict[str, dict] = {}
        self._template: str = "Visa Renewal"
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        selector = ctk.CTkFrame(self, fg_color="transparent")
        selector.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        selector.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(selector, text="Company / Client:").grid(
            row=0, column=0, sticky="w"
        )
        self.company_box = ctk.CTkComboBox(selector, values=[""], command=self._on_company)
        self.company_box.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(selector, text="Service:").grid(row=0, column=2, sticky="w")
        self.service_box = ctk.CTkComboBox(
            selector, values=[""], command=self._on_service, state="readonly"
        )
        self.service_box.grid(row=0, column=3, sticky="ew")

        card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        card.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)
        self.checklist_title = ctk.CTkLabel(
            header,
            text="Renewal document checklist",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        )
        self.checklist_title.grid(row=0, column=0, sticky="w")
        self.progress_label = ctk.CTkLabel(
            header, text="0 of 0", text_color=TEXT_MUTED, anchor="e"
        )
        self.progress_label.grid(row=0, column=1, sticky="e")
        self.countdown = ctk.CTkLabel(
            card,
            text="Select a company and a service to plan the renewal.",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.countdown.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        self.progress_bar = ctk.CTkProgressBar(card)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))

        self.scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.scroll.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.scroll.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))
        ctk.CTkButton(
            footer,
            text="Reset checklist",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._reset_all,
        ).pack(side="left")
        ctk.CTkLabel(
            footer,
            text="Tick items as they arrive; the bar shows overall readiness.",
            text_color=TEXT_MUTED,
        ).pack(side="right")

        self._renewals_tree = None

    def _selected_client_id(self) -> int | None:
        name = self.company_box.get().strip()
        if not name:
            return None
        # Lookup only — never create a client as a side effect of reading.
        return self.app.db.client_id_by_name(name)

    def _fill_combo(self, current: str) -> None:
        names = self.app.db.list_client_names()
        _fill_combo(self.company_box, names, current)

    def select_client(self, name: str) -> None:
        self._fill_combo(name)

    def _on_company(self, _choice: str) -> None:
        self.refresh()

    def _on_service(self, _choice: str) -> None:
        self.refresh()

    def _fill_service_box(self) -> list[dict]:
        """Return the client's renewal services, sorted by nearest expiry, and
        populate the service selector (auto-selecting the nearest one)."""
        client_id = self._selected_client_id()
        if client_id is None:
            return []
        services = [
            item
            for item in self.app.db.list_client_services(client_id)
            if item.get("expiry_date")
        ]
        services.sort(
            key=lambda s: (
                effective_expiry_date(
                    s.get("expiry_date"), s.get("document_type")
                )
                or ""
            )
        )
        labels: list[str] = []
        seen: set[str] = set()
        self._service_by_value.clear()
        for item in services:
            base = item.get("document_type") or "Service"
            label = base if base not in seen else f"{base} — {item.get('expiry_date')}"
            seen.add(base)
            labels.append(label)
            self._service_by_value[label] = item
        current = self.service_box.get()
        self.service_box.configure(values=labels)
        if labels:
            self.service_box.set(current if current in labels else labels[0])
        else:
            self.service_box.set("")
        return services

    def refresh(self) -> None:
        self._fill_combo(self.company_box.get())
        client_id = self._selected_client_id()
        if client_id is None:
            self._fill_service_box()
            self.countdown.configure(
                text="Select a company and a service to plan the renewal.",
                text_color=TEXT_MUTED,
            )
            self.checklist_title.configure(text="Renewal document checklist")
            self._clear_checklist()
            return
        client = self.company_box.get().strip()
        services = self._fill_service_box()
        if not services:
            self.countdown.configure(
                text="No renewal service with an expiry date set for this client.",
                text_color=TEXT_MUTED,
            )
            self.checklist_title.configure(text="Renewal document checklist")
            self._clear_checklist()
            return

        service = self._service_by_value.get(self.service_box.get())
        if service is None:
            return
        left = days_until(
            effective_expiry_date(service.get("expiry_date"), service.get("document_type"))
        )
        if left is None:
            self.countdown.configure(
                text="No renewal expiry date set for this service.",
                text_color=TEXT_MUTED,
            )
            return

        document_type = service.get("document_type") or ""
        template = renewal_template_for(document_type) or GENERAL_RENEWAL_TEMPLATE_NAME
        self._template = template
        tag = classify_expiry(left)
        if left < 0:
            detail = f"expired {abs(left)} day(s) ago"
        elif left == 0:
            detail = "expires today"
        else:
            detail = f"{left} day(s) left"
        tag_color = {
            "red": ("#b91c1c", "#f87171"),
            "orange": ("#b45309", "#fbbf24"),
            "yellow": ("#a16207", "#fde047"),
            "green": ("#15803d", "#4ade80"),
        }.get(tag, ("gray10", "gray90"))
        self.countdown.configure(
            text=f"{document_type} — {detail}", text_color=tag_color
        )
        self.app.set_status(
            f"Renewal for {client}: {document_type} — {detail} ({template})."
        )

        self.app.db.ensure_renewal_checklist(client_id, template)
        items = self.app.db.list_renewal_checklist(client_id, template)
        self.checklist_title.configure(text=f"{template} checklist — {client}")
        self._rebuild_checklist(items)

    def _clear_checklist(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        self._checkboxes.clear()
        self.progress_label.configure(text="0 of 0")
        self.progress_bar.set(0)

    def _rebuild_checklist(self, items: list[dict]) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        self._checkboxes.clear()
        for row, item in enumerate(items):
            item_id = int(item["id"])
            done = bool(item.get("done"))
            checkbox = ctk.CTkCheckBox(
                self.scroll,
                text=item.get("item") or "",
                command=lambda iid=item_id: self._toggle(iid),
            )
            checkbox.grid(row=row, column=0, sticky="w", padx=8, pady=4)
            if done:
                checkbox.select()
            else:
                checkbox.deselect()
            self._checkboxes[item_id] = checkbox
        self._update_progress()

    def _update_progress(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            return
        done, total = self.app.db.renewal_checklist_progress(client_id, self._template)
        self.progress_label.configure(text=f"{done} of {total}")
        self.progress_bar.set(done / total if total else 0)

    def _toggle(self, item_id: int) -> None:
        checkbox = self._checkboxes.get(item_id)
        if checkbox is None:
            return
        self.app.db.set_renewal_item_done(item_id, bool(checkbox.get()))
        self._update_progress()

    def _reset_all(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            return
        items = self.app.db.list_renewal_checklist(client_id, self._template)
        for item in items:
            self.app.db.set_renewal_item_done(int(item["id"]), False)
        fresh = self.app.db.list_renewal_checklist(client_id, self._template)
        self._rebuild_checklist(fresh)
        self.feedback.success("Renewal checklist reset — all items to do.")


class ServicePipelinePanel(ctk.CTkFrame):
    """9-Step Client-to-Supplier pipeline tracker (service engagement lifecycle)."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(top, text="Client:").grid(row=0, column=0, sticky="w")
        self.pipe_client = ctk.CTkComboBox(top, values=[""])
        self.pipe_client.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ctk.CTkLabel(top, text="Service:").grid(row=0, column=2, sticky="w")
        self.pipe_service = ctk.CTkComboBox(
            top, values=self.app.db.list_service_types(), state="readonly"
        )
        self.pipe_service.grid(row=0, column=3, sticky="ew", padx=(0, 12))
        ctk.CTkButton(
            top, text="Add to pipeline", width=130, command=self._add_item
        ).grid(row=0, column=4)

        pipeline_card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        pipeline_card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        pipeline_card.grid_columnconfigure(0, weight=1)
        pipeline_card.grid_rowconfigure(2, weight=1)
        title_row = ctk.CTkFrame(pipeline_card, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            title_row,
            text="Service pipeline",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self.summary = ctk.CTkLabel(
            title_row, text="", text_color=TEXT_MUTED, anchor="e"
        )
        self.summary.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.pipe_tree = ThemedTreeview(
            pipeline_card,
            columns=(
                ("client", "Client", 170),
                ("service", "Service", 220),
                ("step", "Step", 70),
                ("status", "Status", 260),
                ("updated", "Updated", 120),
            ),
            on_double_click=self._advance_item,
        )
        self.pipe_tree.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew")
        controls.grid_columnconfigure(4, weight=1)
        ctk.CTkLabel(controls, text="Set step:").grid(row=0, column=0, sticky="w")
        self.step_menu = ctk.CTkOptionMenu(
            controls,
            values=list(PIPELINE_STEPS),
        )
        self.step_menu.set(PIPELINE_STEPS[0])
        self.step_menu.grid(row=0, column=1, sticky="w", padx=(4, 8))
        ctk.CTkButton(controls, text="Apply", width=70, command=self._set_step).grid(
            row=0, column=2
        )
        ctk.CTkButton(
            controls, text="Advance step", width=120, command=self._advance_item
        ).grid(row=0, column=3, padx=(8, 0))
        ctk.CTkButton(
            controls,
            text="Delete",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._delete_item,
        ).grid(row=0, column=5, padx=(8, 0))
        ctk.CTkLabel(
            controls,
            text="Double-click a row to advance. Steps 3 and 7 are the money milestones.",
            text_color=TEXT_MUTED,
        ).grid(row=0, column=4, sticky="e", padx=(12, 0))

    def refresh(self) -> None:
        self.pipe_tree.apply_theme()
        _fill_combo(self.pipe_client, self.app.db.list_client_names(), self.pipe_client.get())
        self.pipe_service.configure(values=self.app.db.list_service_types())
        items = self.app.db.list_pipeline_items()
        rows: list[tuple] = []
        iids: list[str] = []
        tags: list[list[str]] = []
        for item in items:
            step = max(1, min(int(item["step"]), PIPELINE_MAX_STEP))
            status = PIPELINE_STEPS[step - 1]
            tag = (
                "done"
                if step == PIPELINE_MAX_STEP
                else ("wip" if step in (4, 5, 6, 7, 8) else "")
            )
            rows.append(
                (
                    item.get("client_name") or "Unassigned",
                    item["service"],
                    f"{step}/{PIPELINE_MAX_STEP}",
                    status,
                    item.get("updated_at") or "",
                )
            )
            iids.append(str(item["id"]))
            tags.append([tag] if tag else [])
        self.pipe_tree.set_rows(rows, iids=iids, tags=tags)
        summary = self.app.db.pipeline_summary()
        self.summary.configure(
            text=f"{summary['total']} engagement(s) tracked — {summary['completed']} completed."
        )

    def _refresh_tasks_panel(self) -> None:
        view = self.app._views.get("database_tasks")
        if view is not None and hasattr(view, "tasks_panel"):
            view.tasks_panel.refresh()

    def _add_item(self) -> None:
        name = self.pipe_client.get().strip()
        service = self.pipe_service.get().strip()
        if not name or not service:
            self.feedback.error("Select a client and a service.")
            return
        if service not in self.app.db.list_service_types():
            self.feedback.error(
                "Pick a service from the list — add new services in Settings."
            )
            return
        client_id = self.app.db.get_or_create_client(name)
        self.app.db.add_pipeline_item(client_id=client_id, service=service)
        self.pipe_service.set("")
        self.feedback.success(f"Added {name} — {service} to the pipeline (step 1).")
        self.refresh()
        self._refresh_tasks_panel()

    def _selected_item_id(self) -> int | None:
        iid = self.pipe_tree.selected_iid()
        if iid is None:
            return None
        return int(iid)

    def _advance_item(self, _iid: str | None = None) -> None:
        item_id = _iid or self.pipe_tree.selected_iid()
        if item_id is None:
            self.feedback.error("Select a pipeline item first.")
            return
        item = self.app.db.get_pipeline_item(int(item_id))
        if item and int(item["step"]) >= PIPELINE_MAX_STEP:
            self.feedback.info("This item is already completed.")
            return
        self.app.db.advance_pipeline(int(item_id))
        self.feedback.success("Pipeline advanced one step.")
        self.refresh()
        self._refresh_tasks_panel()

    def _set_step(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            self.feedback.error("Select a pipeline item first.")
            return
        try:
            step = int(self.step_menu.get().split(".")[0])
        except ValueError:
            step = 1
        if step < 1:
            step = 1
        if step > PIPELINE_MAX_STEP:
            step = PIPELINE_MAX_STEP
        self.app.db.set_pipeline_step(item_id, step)
        self.feedback.success(f"Step set to {PIPELINE_STEPS[step - 1]}.")
        self.refresh()
        self._refresh_tasks_panel()

    def _delete_item(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            self.feedback.error("Select a pipeline item first.")
            return
        if not messagebox.askyesno(
            "Delete pipeline item",
            "Delete this pipeline item?\n\nIts pipeline tasks will also be removed.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_pipeline_item(item_id)
        self.feedback.success("Pipeline item deleted.")
        self.refresh()
        self._refresh_tasks_panel()


class SuppliersPanel(ctk.CTkFrame):
    """Supplier directory + supplier services + pending supplier payments (AP)."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._selected_supplier_id: int | None = None
        self._editing_svc_id: int | None = None
        self._editing_payment_id: int | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=0, column=0, sticky="nsew")
        for name in ("Suppliers", "Supplier Services", "Payments (AP)"):
            tabs.add(name)
            tab = tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_propagate(False)

        self._tabs = tabs

        # ---- Tab 1: Suppliers directory ----
        sup_tab = tabs.tab("Suppliers")
        sup_scroll = ctk.CTkScrollableFrame(sup_tab, fg_color="transparent")
        sup_scroll.grid(row=0, column=0, sticky="nsew")
        sup_scroll.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(sup_scroll, corner_radius=CARD_RADIUS)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card, text="Supplier directory",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Name").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.sup_name = ctk.CTkEntry(form, placeholder_text="Required")
        self.sup_name.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Company").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.sup_company = ctk.CTkEntry(form)
        self.sup_company.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Contact").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.sup_contact = ctk.CTkEntry(form)
        self.sup_contact.grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)
        ctk.CTkLabel(form, text="Notes").grid(row=2, column=0, sticky="nw", padx=(0, 8), pady=4)
        self.sup_notes = ctk.CTkTextbox(form, height=100)
        self.sup_notes.grid(row=2, column=1, columnspan=3, sticky="ew", pady=4)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        ctk.CTkButton(btns, text="Save", width=100, command=self._save_supplier).pack(side="left")
        ctk.CTkButton(
            btns, text="New", width=70, fg_color="transparent", border_width=1,
            command=self._new_supplier,
        ).pack(side="left", padx=(8, 0))

        self.supplier_tree = ThemedTreeview(
            card,
            columns=(
                ("name", "Name", 160),
                ("company", "Company", 140),
                ("contact", "Contact", 150),
                ("notes", "Notes", 260),
            ),
            on_select=self._on_supplier_select,
            showheight=8,
        )
        self.supplier_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        ctk.CTkButton(
            card, text="Delete selected", fg_color="transparent", border_width=1,
            command=self._delete_supplier,
        ).grid(row=4, column=0, sticky="w", padx=16, pady=(0, 14))

        # ---- Tab 2: Supplier services ----
        svc_tab = tabs.tab("Supplier Services")
        svc_scroll = ctk.CTkScrollableFrame(svc_tab, fg_color="transparent")
        svc_scroll.grid(row=0, column=0, sticky="nsew")
        svc_scroll.grid_columnconfigure(0, weight=1)

        svc_card = ctk.CTkFrame(svc_scroll, corner_radius=CARD_RADIUS)
        svc_card.grid(row=0, column=0, sticky="ew")
        svc_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            svc_card, text="Supplier services — tracked per supplier",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        hint = ctk.CTkLabel(
            svc_card,
            text="Select a supplier in the Suppliers tab first, then add services here.",
            text_color=("gray40", "gray60"),
            anchor="w",
        )
        hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        svc_form = ctk.CTkFrame(svc_card, fg_color="transparent")
        svc_form.grid(row=2, column=0, sticky="ew", padx=16)
        svc_form.grid_columnconfigure(1, weight=1)
        svc_form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(svc_form, text="Company").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.svc_company = ctk.CTkEntry(svc_form, placeholder_text="Company name")
        self.svc_company.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(svc_form, text="Service").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.svc_service = ctk.CTkEntry(svc_form, placeholder_text="e.g. Non-VAT Address")
        self.svc_service.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(svc_form, text="Expiry date").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.svc_expiry_var = ctk.StringVar()
        DatePickerField(svc_form, var=self.svc_expiry_var).grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(svc_form, text="Notes").grid(row=1, column=2, sticky="w", padx=(12, 8), pady=4)
        self.svc_notes = ctk.CTkEntry(svc_form, placeholder_text="Optional")
        self.svc_notes.grid(row=1, column=3, sticky="ew", pady=4)

        svc_btns = ctk.CTkFrame(svc_card, fg_color="transparent")
        svc_btns.grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 4))
        ctk.CTkButton(svc_btns, text="Add service", width=110, command=self._add_supplier_service).pack(side="left")
        ctk.CTkButton(
            svc_btns, text="Edit", width=70, command=self._edit_supplier_service,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            svc_btns, text="Delete", width=70, fg_color="transparent", border_width=1,
            command=self._delete_supplier_service,
        ).pack(side="left", padx=(8, 0))

        self.supplier_svc_tree = ThemedTreeview(
            svc_card,
            columns=(
                ("company", "Company", 200),
                ("service", "Service", 200),
                ("expiry", "Expiry date", 120),
                ("notes", "Notes", 200),
            ),
            showheight=10,
        )
        self.supplier_svc_tree.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))

        # ---- Tab 3: Payments (AP) ----
        pay_tab = tabs.tab("Payments (AP)")
        pay_scroll = ctk.CTkScrollableFrame(pay_tab, fg_color="transparent")
        pay_scroll.grid(row=0, column=0, sticky="nsew")
        pay_scroll.grid_columnconfigure(0, weight=1)

        pay_card = ctk.CTkFrame(pay_scroll, corner_radius=CARD_RADIUS)
        pay_card.grid(row=0, column=0, sticky="ew")
        pay_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            pay_card, text="Supplier payments (AP)",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        pay_form = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_form.grid(row=1, column=0, sticky="ew", padx=16)
        pay_form.grid_columnconfigure(1, weight=1)
        pay_form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(pay_form, text="Supplier").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pay_supplier = ctk.CTkComboBox(pay_form, values=[""])
        self.pay_supplier.grid(row=0, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Client").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        self.pay_client = ctk.CTkComboBox(pay_form, values=[""])
        self.pay_client.grid(row=0, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Amount (THB)").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pay_amount = ctk.CTkEntry(pay_form, placeholder_text="e.g. 15000")
        self.pay_amount.bind("<FocusOut>", lambda _e: self._format_pay_amount())
        self.pay_amount.grid(row=1, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Due date").grid(row=1, column=2, sticky="w", padx=(12, 8), pady=4)
        self.pay_due_var = ctk.StringVar()
        DatePickerField(pay_form, var=self.pay_due_var).grid(row=1, column=3, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Payment date").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.pay_date_var = ctk.StringVar()
        DatePickerField(pay_form, var=self.pay_date_var).grid(row=2, column=1, sticky="ew", pady=4)
        ctk.CTkLabel(pay_form, text="Notes").grid(row=2, column=2, sticky="w", padx=(12, 8), pady=4)
        self.pay_notes = ctk.CTkEntry(pay_form)
        self.pay_notes.grid(row=2, column=3, sticky="ew", pady=4)
        pay_form_btns = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_form_btns.grid(row=2, column=0, sticky="w", padx=16, pady=(8, 4))
        self.pay_save_btn = ctk.CTkButton(
            pay_form_btns, text="Add payment", width=120, command=self._save_payment
        )
        self.pay_save_btn.pack(side="left")
        ctk.CTkButton(
            pay_form_btns, text="Edit", width=70, command=self._edit_payment
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            pay_form_btns, text="New", width=70, fg_color="transparent", border_width=1,
            command=self._new_payment,
        ).pack(side="left", padx=(8, 0))

        self.pay_tree = ThemedTreeview(
            pay_card,
            columns=(
                ("supplier", "Supplier", 150),
                ("client", "Client", 130),
                ("amount", "Amount", 90),
                ("due", "Due date", 90),
                ("paid", "Paid", 60),
                ("paid_date", "Paid date", 90),
                ("notes", "Notes", 160),
            ),
            showheight=10,
        )
        self.pay_tree.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        pay_btns = ctk.CTkFrame(pay_card, fg_color="transparent")
        pay_btns.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkButton(pay_btns, text="Mark paid", width=110, command=self._mark_paid).pack(side="left")
        ctk.CTkButton(
            pay_btns, text="Delete", width=90, fg_color="transparent", border_width=1,
            command=self._delete_payment,
        ).pack(side="left", padx=(8, 0))

    def refresh(self) -> None:
        self.supplier_tree.apply_theme()
        self.supplier_svc_tree.apply_theme()
        self.pay_tree.apply_theme()
        suppliers = self.app.db.list_suppliers()
        self.supplier_tree.set_rows(
            [
                (
                    s["name"],
                    s.get("company_name") or "",
                    s.get("contact") or "",
                    (s.get("notes") or "")[:80],
                )
                for s in suppliers
            ],
            iids=[str(s["id"]) for s in suppliers],
        )
        _fill_combo(
            self.pay_supplier, [s["name"] for s in suppliers], self.pay_supplier.get()
        )
        _fill_combo(self.pay_client, self.app.db.list_client_names(), self.pay_client.get())
        self._refresh_supplier_services()
        payments = self.app.db.list_supplier_payments()
        rows: list[tuple] = []
        iids: list[str] = []
        tags: list[list[str]] = []
        for payment in payments:
            rows.append(
                (
                    payment.get("supplier_name") or "?",
                    payment.get("client_name") or "—",
                    format_thousands(payment.get("amount")) if payment.get("amount") else "—",
                    payment.get("due_date") or "—",
                    "Yes" if payment.get("paid") else "No",
                    payment.get("paid_date") or "—",
                    payment.get("notes") or "—",
                )
            )
            iids.append(str(payment["id"]))
            tags.append(["completed"] if payment.get("paid") else [])
        self.pay_tree.set_rows(rows, iids=iids, tags=tags)

    def _format_pay_amount(self) -> None:
        value = format_thousands(self.pay_amount.get())
        self.pay_amount.delete(0, "end")
        self.pay_amount.insert(0, value)

    def _on_supplier_select(self, iid: str | None) -> None:
        if iid is None:
            self._selected_supplier_id = None
            return
        supplier = self.app.db.get_supplier(int(iid))
        if supplier is None:
            self._selected_supplier_id = None
            return
        self._selected_supplier_id = int(supplier["id"])
        for entry, value in (
            (self.sup_name, supplier["name"]),
            (self.sup_company, supplier.get("company_name") or ""),
            (self.sup_contact, supplier.get("contact") or ""),
        ):
            entry.delete(0, "end")
            entry.insert(0, value)
        self.sup_notes.delete("1.0", "end")
        self.sup_notes.insert("1.0", supplier.get("notes") or "")
        self._refresh_supplier_services()

    def _save_supplier(self) -> None:
        name = self.sup_name.get().strip()
        if not name:
            self.feedback.error("Enter a supplier name.")
            return
        notes = self.sup_notes.get("1.0", "end-1c").strip()
        try:
            if self._selected_supplier_id:
                self.app.db.update_supplier(
                    self._selected_supplier_id,
                    name=name,
                    company_name=self.sup_company.get(),
                    contact=self.sup_contact.get(),
                    notes=notes,
                )
            else:
                self.app.db.add_supplier(
                    name=name,
                    company_name=self.sup_company.get(),
                    contact=self.sup_contact.get(),
                    notes=notes,
                )
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Supplier saved.")
        self._new_supplier()
        self.refresh()

    def _new_supplier(self) -> None:
        self._selected_supplier_id = None
        self.supplier_tree.tree.selection_remove(*self.supplier_tree.tree.selection())
        for entry in (self.sup_name, self.sup_company, self.sup_contact):
            entry.delete(0, "end")
        self.sup_notes.delete("1.0", "end")

    def _delete_supplier(self) -> None:
        iid = self.supplier_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a supplier first.")
            return
        if not messagebox.askyesno(
            "Delete supplier",
            "Delete this supplier?\n\nAll of their payment records will be removed too. "
            "This cannot be undone.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_supplier(int(iid))
        self.feedback.success("Supplier deleted (payments removed too).")
        self._new_supplier()
        self.refresh()

    def _save_payment(self) -> None:
        supplier_name = self.pay_supplier.get().strip()
        if not supplier_name:
            self.feedback.error("Select or type a supplier name.")
            return
        supplier_id = self.app.db.get_or_create_supplier(supplier_name)
        client_id: int | None = None
        client_name = self.pay_client.get().strip()
        if client_name:
            client_id = self.app.db.client_id_by_name(client_name)
            if client_id is None:
                self.feedback.error(
                    f"Client '{client_name}' does not exist — add the client first."
                )
                return
        raw_amount = self.pay_amount.get().strip()
        pay_date = parse_flexible_date(self.pay_date_var.get().strip())
        if self.pay_date_var.get().strip() and pay_date is None:
            self.feedback.error("Enter a valid payment date (YYYY-MM-DD or DD/MM/YYYY).")
            return
        due_date = parse_flexible_date(self.pay_due_var.get().strip())
        if self.pay_due_var.get().strip() and due_date is None:
            self.feedback.error("Enter a valid due date (YYYY-MM-DD or DD/MM/YYYY).")
            return
        fields = dict(
            supplier_id=supplier_id,
            client_id=client_id,
            amount=sanitize_amount(raw_amount) if raw_amount else None,
            due_date=due_date,
            paid_date=pay_date,
            notes=self.pay_notes.get().strip() or None,
        )
        if self._editing_payment_id:
            self.app.db.update_supplier_payment(self._editing_payment_id, **fields)
            self.feedback.success("Supplier payment updated.")
        else:
            self.app.db.add_supplier_payment(**fields)
            self.feedback.success("Supplier payment recorded.")
        self._new_payment()
        self.refresh()

    def _edit_payment(self) -> None:
        iid = self.pay_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a payment to edit.")
            return
        payment = self.app.db.get_supplier_payment(int(iid))
        if payment is None:
            self.feedback.error("Payment record not found.")
            return
        self._editing_payment_id = int(iid)
        self.pay_save_btn.configure(text="Save payment")
        _fill_combo(
            self.pay_supplier,
            [s["name"] for s in self.app.db.list_suppliers()],
            payment.get("supplier_name") or "",
        )
        _fill_combo(
            self.pay_client,
            self.app.db.list_client_names(),
            payment.get("client_name") or "",
        )
        self.pay_amount.delete(0, "end")
        if payment.get("amount"):
            self.pay_amount.insert(0, format_thousands(payment["amount"]))
        self.pay_due_var.set(payment.get("due_date") or "")
        self.pay_date_var.set(payment.get("paid_date") or "")
        self.pay_notes.delete(0, "end")
        if payment.get("notes"):
            self.pay_notes.insert(0, payment["notes"])

    def _new_payment(self) -> None:
        self._editing_payment_id = None
        self.pay_save_btn.configure(text="Add payment")
        self.pay_tree.tree.selection_remove(*self.pay_tree.tree.selection())
        self.pay_amount.delete(0, "end")
        self.pay_due_var.set("")
        self.pay_date_var.set("")
        self.pay_notes.delete(0, "end")

    def _mark_paid(self) -> None:
        iid = self.pay_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a payment first.")
            return
        payment = self.app.db.get_supplier_payment(int(iid))
        if payment is None:
            self.feedback.error("Payment record not found.")
            return
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("Mark as paid")
        top.resizable(False, False)
        top.geometry("380x230")
        top.update_idletasks()
        width, height = 380, 230
        x = (self.winfo_rootx() + self.winfo_width() // 2) - width // 2
        y = (self.winfo_rooty() + self.winfo_height() // 2) - height // 2
        top.geometry(f"{width}x{height}+{x}+{y}")
        top.deiconify()
        top.lift()
        top.focus_force()
        make_modal(top)

        ctk.CTkLabel(
            top,
            text=payment.get("supplier_name") or "Supplier",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            top,
            text="Pick the date this payment was actually made.",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=20)

        ctk.CTkLabel(top, text="Payment date", anchor="w").grid(
            row=2, column=0, sticky="w", padx=20, pady=(10, 2)
        )
        date_var = ctk.StringVar(value=payment.get("paid_date") or date.today().isoformat())
        DatePickerField(top, var=date_var).grid(row=3, column=0, sticky="ew", padx=20)

        def _do() -> None:
            value = date_var.get().strip()
            parsed = parse_flexible_date(value)
            if not parsed:
                self.feedback.error("Enter a valid payment date.")
                return
            self.app.db.set_supplier_payment_paid(int(iid), True, paid_date=parsed)
            top.destroy()
            self.feedback.success("Payment marked as paid.")
            self.refresh()

        ctk.CTkButton(top, text="Confirm paid", command=_do).grid(
            row=4, column=0, sticky="ew", padx=20, pady=(12, 18)
        )

    def _delete_payment(self) -> None:
        iid = self.pay_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a payment first.")
            return
        if not messagebox.askyesno(
            "Delete payment",
            "Delete this payment record?",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_supplier_payment(int(iid))
        self.feedback.success("Payment deleted.")
        self.refresh()

    # ---- supplier services (company / service / expiry) ----
    def _refresh_supplier_services(self) -> None:
        if self._selected_supplier_id is None:
            self.supplier_svc_tree.set_rows([])
            return
        services = self.app.db.list_supplier_services(self._selected_supplier_id)
        self.supplier_svc_tree.set_rows(
            [
                (
                    s["company_name"],
                    s["service_type"],
                    s.get("expiry_date") or "—",
                    s.get("notes") or "",
                )
                for s in services
            ],
            iids=[str(s["id"]) for s in services],
        )

    def _add_supplier_service(self) -> None:
        if self._selected_supplier_id is None:
            self.feedback.error("Select a supplier first (Suppliers tab).")
            return
        company = self.svc_company.get().strip()
        service = self.svc_service.get().strip()
        if not company or not service:
            self.feedback.error("Enter company and service name.")
            return
        expiry = parse_flexible_date(self.svc_expiry_var.get().strip())
        if self.svc_expiry_var.get().strip() and expiry is None:
            self.feedback.error("Enter a valid expiry date (YYYY-MM-DD or DD/MM/YYYY).")
            return
        notes = self.svc_notes.get().strip() or None
        if self._editing_svc_id:
            self.app.db.update_supplier_service(
                self._editing_svc_id,
                company_name=company,
                service_type=service,
                expiry_date=expiry,
                notes=notes,
            )
            self.feedback.success("Supplier service updated.")
        else:
            self.app.db.add_supplier_service(
                supplier_id=self._selected_supplier_id,
                company_name=company,
                service_type=service,
                expiry_date=expiry,
                notes=notes,
            )
            self.feedback.success("Supplier service added.")
        self._clear_svc_form()
        self._refresh_supplier_services()

    def _clear_svc_form(self) -> None:
        self._editing_svc_id = None
        self.svc_company.delete(0, "end")
        self.svc_service.delete(0, "end")
        self.svc_expiry_var.set("")
        self.svc_notes.delete(0, "end")

    def _edit_supplier_service(self) -> None:
        iid = self.supplier_svc_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a service to edit.")
            return
        services = self.app.db.list_supplier_services(self._selected_supplier_id)
        svc = next((s for s in services if str(s["id"]) == iid), None)
        if svc is None:
            return
        self._editing_svc_id = int(iid)
        self.svc_company.delete(0, "end")
        self.svc_company.insert(0, svc["company_name"])
        self.svc_service.delete(0, "end")
        self.svc_service.insert(0, svc["service_type"])
        self.svc_expiry_var.set(svc.get("expiry_date") or "")
        self.svc_notes.delete(0, "end")
        if svc.get("notes"):
            self.svc_notes.insert(0, svc["notes"])

    def _delete_supplier_service(self) -> None:
        iid = self.supplier_svc_tree.selected_iid()
        if iid is None:
            self.feedback.error("Select a service first.")
            return
        if not messagebox.askyesno(
            "Delete supplier service",
            "Delete this supplier service record?",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_supplier_service(int(iid))
        self.feedback.success("Supplier service deleted.")
        self._refresh_supplier_services()
