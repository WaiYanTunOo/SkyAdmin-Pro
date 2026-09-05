"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.services.file_ops import open_in_file_manager, parse_flexible_date
from skyadmin_pro.services.tracking import (
    classify_expiry,
    days_until,
    effective_expiry_date,
    expiry_label,
)
from skyadmin_pro.services.workflow import create_client_workspace
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField, FeedbackLabel, make_modal, themed_entry


class ClientsExpiryPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        from skyadmin_pro.services.undo_manager import UndoManager

        self._undo = UndoManager()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        left = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        left.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        left.grid_columnconfigure(0, weight=1)
        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        title_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(title_row, text="Company List", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.search_var = ctk.StringVar()
        self._search_after: str | None = None
        self.search_var.trace_add("write", lambda *_args: self._debounced_search())
        themed_entry(
            title_row,
            textvariable=self.search_var,
            placeholder_text="Search name / email",
        ).grid(row=0, column=1, sticky="ew", padx=(12, 8))
        self._group_filter_var = ctk.StringVar(value="All")
        self.group_filter_menu = ctk.CTkOptionMenu(
            title_row, variable=self._group_filter_var,
            values=["All"], width=120, command=lambda _: self._refresh_clients(),
        )
        self.group_filter_menu.grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(
            title_row,
            text="Export to Excel",
            width=130,
            command=self._export_excel,
        ).grid(row=0, column=3, sticky="e", padx=(8, 0))
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
        ctk.CTkButton(actions, text="Add / Edit client", width=125, command=self._open_client_dialog).pack(side="left")
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

        # Batch action row (visible when items are selected)
        batch_row = ctk.CTkFrame(left, fg_color="transparent")
        batch_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 4))
        ctk.CTkLabel(
            batch_row, text="Batch:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#9ca3af",
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            batch_row, text="Delete selected", width=110,
            fg_color="#dc2626", hover_color="#b91c1c",
            command=self._batch_delete,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row, text="Mark Active", width=95,
            fg_color="transparent", border_width=1,
            command=lambda: self._batch_set_status("Active"),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row, text="Mark Inactive", width=95,
            fg_color="transparent", border_width=1,
            command=lambda: self._batch_set_status("Inactive"),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row, text="Undo", width=70,
            fg_color="transparent", border_width=1,
            command=self._undo_last,
        ).pack(side="left")

        right = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
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
        # Refresh group filter options
        groups = self.app.db.list_client_groups()
        group_names = ["All"] + [g["name"] for g in groups]
        self._group_map = {g["name"]: g["id"] for g in groups}
        current = self._group_filter_var.get()
        self.group_filter_menu.configure(values=group_names)
        if current in group_names:
            self._group_filter_var.set(current)
        else:
            self._group_filter_var.set("All")
        self._refresh_client_table()
        clients = self.app.db.list_clients()
        names = [item["name"] for item in clients]
        fill_combo(self.expiry_client, names, self.expiry_client.get())

        documents = self.app.db.list_documents(expiring_only=True)
        rows, iids, tags = [], [], []
        for item in documents:
            eff = effective_expiry_date(item.get("expiry_date"), item.get("document_type"))
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
        self.doc_tree.set_rows(rows, iids=iids, tags=tags, empty_message="No expiring documents match this filter.")

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
        # Apply group filter
        group_filter = self._group_filter_var.get()
        if group_filter != "All":
            group_id = getattr(self, "_group_map", {}).get(group_filter)
            if group_id is not None:
                clients = [c for c in clients if c.get("group_id") == group_id]
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
        self.client_tree.set_rows(rows, iids=iids, tags=tags, empty_message="No clients match this search.")

    def _export_excel(self) -> None:
        view = self.app.get_view("database_tasks")
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
            value=("Inactive" if current.get("status") == "inactive" else "Active") if current else "Active"
        )
        for row, label, var in (
            (0, "Company name", name_var),
            (1, "Contact name", contact_var),
            (2, "Email", email_var),
        ):
            ctk.CTkLabel(body, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
            themed_entry(body, textvariable=var).grid(row=row, column=1, sticky="ew", pady=6)
        ctk.CTkLabel(body, text="Status", anchor="w").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=6)
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

    def _save_client_dialog(self, top, client_id: int | None, name_var, contact_var, email_var, status_var) -> None:
        name = name_var.get().strip()
        if not name:
            self.feedback.error("Enter a company name.")
            return
        contact = contact_var.get().strip()
        email = email_var.get().strip()
        status = "active" if status_var.get() == "Active" else "inactive"
        try:
            from skyadmin_pro.services.client_commands import AddClientCommand, EditClientCommand

            if client_id is None:
                self._undo.execute(
                    AddClientCommand(
                        self.app.db, name=name, contact=contact, email=email, status=status
                    )
                )
                view = self.app.get_view("database_tasks")
                if view is not None and getattr(view, "tasks_panel", None) is not None:
                    view.tasks_panel.refresh()
            else:
                self._undo.execute(
                    EditClientCommand(
                        self.app.db, client_id,
                        name=name, contact_name=contact, email=email, status=status,
                    )
                )
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        top.destroy()
        self.feedback.success(f"Client saved: {name}")
        self.refresh()

    def _undo_last(self) -> None:
        if not self._undo.can_undo():
            self.feedback.info("Nothing to undo.")
            return
        try:
            label = self._undo.undo()
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success(f"Undid: {label}.")
        self.refresh()

    def _on_shortcut_undo(self) -> None:
        self._undo_last()

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
        self.feedback.success(f"Workspace ready: {folder.name}/01_Company_Setup, 02_Accounting, 03_Visa")
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
            "but lose the client link. You can undo once with Ctrl+Z.",
            parent=self.winfo_toplevel(),
        ):
            return
        from skyadmin_pro.services.client_commands import DeleteClientsCommand

        self._undo.execute(DeleteClientsCommand(self.app.db, [int(iid)]))
        self.feedback.success("Client deleted. (Ctrl+Z to undo)")
        self.refresh()

    def _batch_delete(self) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        if not messagebox.askyesno(
            "Batch delete",
            f"Delete {len(iids)} selected client(s)? You can undo once with Ctrl+Z.",
            parent=self.winfo_toplevel(),
        ):
            return
        from skyadmin_pro.services.client_commands import DeleteClientsCommand

        ids = [int(iid) for iid in iids]
        count = self._undo.execute(DeleteClientsCommand(self.app.db, ids))
        self.feedback.success(f"Deleted {count} client(s). (Ctrl+Z to undo)")
        self.refresh()

    def _batch_set_status(self, status: str) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        from skyadmin_pro.services.client_commands import SetStatusCommand

        ids = [int(iid) for iid in iids]
        count = self._undo.execute(SetStatusCommand(self.app.db, ids, status))
        self.feedback.success(f"Updated {count} client(s) to {status}.")
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
        view = self.app.get_view("database_tasks")
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
