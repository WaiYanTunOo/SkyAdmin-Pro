"""Database & Tasks: live task table, courier tracker, clients, and Excel export."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    COURIER_DRIVERS,
    GENERAL_RENEWAL_TEMPLATE_NAME,
    PIPELINE_MAX_STEP,
    PIPELINE_STEPS,
    SERVICE_PROGRESS,
    TASK_CATEGORIES,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
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
from skyadmin_pro.services.tracking import (
    classify_expiry,
    days_until,
    effective_expiry_date,
    expiry_label,
)
from skyadmin_pro.services.workflow import (
    create_client_workspace,
    repair_client_workspaces,
    resolve_client_folder,
)
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.theme import CARD_CONTENT_PADX, CARD_RADIUS, CARD_TITLE_SIZE, TEXT_FAINT, TEXT_MUTED
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import DatePickerField, FeedbackLabel, make_modal, MonthStatusPanel
from skyadmin_pro.ui.views.company_details import CompanyDetailsPanel

NONE_TASK = "(none)"


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
        fill_combo(self.client_box, names, current)

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
        fill_combo(self.client_box, self.app.db.list_client_names(), self.client_box.get())
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
        fill_combo(self.expiry_client, names, self.expiry_client.get())

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
        fill_combo(self.company_box, names, current)

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
        fill_combo(self.pipe_client, self.app.db.list_client_names(), self.pipe_client.get())
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
        fill_combo(
            self.pay_supplier, [s["name"] for s in suppliers], self.pay_supplier.get()
        )
        fill_combo(self.pay_client, self.app.db.list_client_names(), self.pay_client.get())
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
        fill_combo(
            self.pay_supplier,
            [s["name"] for s in self.app.db.list_suppliers()],
            payment.get("supplier_name") or "",
        )
        fill_combo(
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
