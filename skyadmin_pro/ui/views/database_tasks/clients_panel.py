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
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField, FeedbackLabel, make_modal, themed_entry


class ClientsExpiryPanel(ctk.CTkFrame):
    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._refresh_seq = 0
        self._table_seq = 0
        self._page = 0
        self._page_size = 250
        self._has_more = False
        from skyadmin_pro.services.undo_manager import UndoManager

        self._undo = UndoManager()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._scroll = CanvasScrollFrame(self)
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.content.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(self._scroll.content, corner_radius=CARD_RADIUS)
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
            title_row,
            variable=self._group_filter_var,
            values=["All"],
            width=120,
            command=lambda _: self._refresh_clients(),
        )
        self.group_filter_menu.grid(row=0, column=2, padx=(0, 4))
        ctk.CTkLabel(
            title_row,
            text="(this PC only)",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=3, padx=(0, 8), sticky="w")
        ctk.CTkButton(
            title_row,
            text="Export to Excel",
            width=130,
            command=self._export_excel,
        ).grid(row=0, column=4, sticky="e", padx=(8, 0))
        self.client_tree = ThemedTreeview(
            left,
            columns=(
                ("company", "Company name", 210),
                ("contact", "Contact", 150),
                ("email", "Email", 220),
                ("status", "Status", 90),
            ),
            showheight=9,
            table_id="clients",
            db=self.app.db,
            selectmode="extended",
        )
        self.client_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 4))
        self.client_tree.tree.bind("<<TreeviewSelect>>", self._on_client_tree_select, add="+")
        left.grid_rowconfigure(1, weight=1)
        client_pager = ctk.CTkFrame(left, fg_color="transparent")
        client_pager.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))
        self.client_prev = ctk.CTkButton(
            client_pager,
            text="◀ Prev",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._client_prev_page,
        )
        self.client_prev.pack(side="left")
        self.client_page_label = ctk.CTkLabel(client_pager, text="Page 1", text_color=TEXT_MUTED)
        self.client_page_label.pack(side="left", padx=10)
        self.client_next = ctk.CTkButton(
            client_pager,
            text="Next ▶",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._client_next_page,
        )
        self.client_next.pack(side="left")
        self.client_page_size = ctk.CTkOptionMenu(
            client_pager,
            values=["100", "250", "500", "1000"],
            width=90,
            command=self._on_client_page_size,
        )
        self.client_page_size.set("250")
        self.client_page_size.pack(side="right")
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 4))
        ctk.CTkButton(actions, text="Add / Edit client", width=125, command=self._open_client_dialog).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Groups…",
            width=85,
            fg_color="transparent",
            border_width=1,
            command=self._manage_groups,
        ).pack(side="left", padx=(8, 0))
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

        # Batch action row — Ctrl/Shift+click multi-select (selectmode extended)
        batch_row = ctk.CTkFrame(left, fg_color="transparent")
        batch_row.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 8))
        ctk.CTkLabel(
            batch_row,
            text="Batch:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(0, 6))
        self._batch_selection_label = ctk.CTkLabel(
            batch_row,
            text="0 selected",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_MUTED,
        )
        self._batch_selection_label.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            batch_row,
            text="Archive selected",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._batch_archive,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row,
            text="Delete selected",
            width=110,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._batch_delete,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row,
            text="Mark Active",
            width=95,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._batch_set_status("active"),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row,
            text="Mark Inactive",
            width=95,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._batch_set_status("inactive"),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row,
            text="Assign group…",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._batch_assign_group,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            batch_row,
            text="Undo",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._undo_last,
        ).pack(side="left")

        right = ctk.CTkFrame(self._scroll.content, corner_radius=CARD_RADIUS)
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
            table_id="clients.expiry",
            db=self.app.db,
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
        from skyadmin_pro.ui.async_ui import run_background

        self.client_tree.apply_theme()
        self.doc_tree.apply_theme()
        try:
            current_group = self._group_filter_var.get()
        except Exception:
            current_group = "All"
        try:
            current_expiry = self.expiry_client.get()
        except Exception:
            current_expiry = ""

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db
        self.feedback.info("Loading clients…")
        # Client table has its own seq; kick it (it shows its own status).
        self._refresh_client_table()

        def work():
            return {
                "groups": db.list_client_groups(),
                "clients": db.list_clients(),
                "documents": db.list_documents(expiring_only=True),
                "current_group": current_group,
                "current_expiry": current_expiry,
            }

        def on_success(payload) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            groups = payload["groups"]
            group_names = ["All"] + [g["name"] for g in groups]
            self._group_map = {g["name"]: g["id"] for g in groups}
            self.group_filter_menu.configure(values=group_names)
            cur = payload["current_group"]
            self._group_filter_var.set(cur if cur in group_names else "All")
            names = [item["name"] for item in payload["clients"]]
            fill_combo(self.expiry_client, names, payload["current_expiry"])
            rows, iids, tags = [], [], []
            for item in payload["documents"]:
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
            self._scroll._on_content_configure()
            self.feedback.clear()

        def on_error(msg: str) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            self.feedback.error(f"Clients failed to load: {msg}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)

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
        self._page = 0
        self._refresh_client_table()

    def _refresh_clients(self) -> None:
        """Group-filter menu legacy entry point (was missing → AttributeError)."""
        self._page = 0
        self._refresh_client_table()

    def _client_prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._refresh_client_table()

    def _client_next_page(self) -> None:
        if self._has_more:
            self._page += 1
            self._refresh_client_table()

    def _on_client_page_size(self, value: str) -> None:
        try:
            self._page_size = max(50, int(value))
        except ValueError:
            self._page_size = 250
        self._page = 0
        self._refresh_client_table()

    def _update_client_pager(self, shown: int) -> None:
        label = f"Page {self._page + 1} · {shown} shown"
        if self._has_more:
            label += " · more…"
        try:
            self.client_page_label.configure(text=label)
            self.client_prev.configure(state="normal" if self._page > 0 else "disabled")
            self.client_next.configure(state="normal" if self._has_more else "disabled")
        except Exception:
            pass

    def _refresh_client_table(self) -> None:
        from skyadmin_pro.ui.async_ui import run_background

        try:
            query = self.search_var.get()
        except Exception:
            query = ""
        try:
            group_filter = self._group_filter_var.get()
        except Exception:
            group_filter = "All"
        group_map = dict(getattr(self, "_group_map", {}))
        page, page_size = self._page, self._page_size

        self._table_seq += 1
        seq = self._table_seq
        db = self.app.db

        def work():
            if group_filter != "All":
                gid = group_map.get(group_filter)
                # Group subsets are small: filter in Python, then page.
                clients = db.search_clients(query)
                if gid is not None:
                    clients = [c for c in clients if c.get("group_id") == gid]
                window = clients[page * page_size : page * page_size + page_size + 1]
                return window
            return db.search_clients(query, limit=page_size + 1, offset=page * page_size)

        def on_success(clients) -> None:
            if seq != self._table_seq or not self.winfo_exists():
                return
            self._has_more = len(clients) > self._page_size
            shown = clients[: self._page_size]
            rows, iids, tags = [], [], []
            for item in shown:
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
            self._update_client_pager(len(shown))
            self._scroll._on_content_configure()

        def on_error(msg: str) -> None:
            if seq != self._table_seq or not self.winfo_exists():
                return
            self.feedback.error(f"Client search failed: {msg}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)

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

    def _manage_groups(self) -> None:
        from skyadmin_pro.ui.widgets import make_modal, themed_entry

        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("Manage client groups")
        top.resizable(False, False)
        top.geometry("400x400")
        make_modal(top)
        body = ctk.CTkFrame(top, corner_radius=CARD_RADIUS)
        body.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(body, text="Groups", anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 2))
        ctk.CTkLabel(
            body,
            text="Groups are this PC only — not synced across devices.",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))
        group_var = ctk.StringVar(value="")
        group_menu = ctk.CTkOptionMenu(body, variable=group_var, values=[""], width=280)
        group_menu.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        name_var = ctk.StringVar(value="")
        themed_entry(body, textvariable=name_var, placeholder_text="Group name").grid(
            row=3, column=0, sticky="ew", pady=(0, 6)
        )
        msg = ctk.CTkLabel(body, text="", anchor="w")
        msg.grid(row=4, column=0, sticky="ew", pady=(0, 6))

        def id_map() -> dict[str, int]:
            return {g["name"]: g["id"] for g in self.app.db.list_client_groups()}

        def refresh_menu(select: str = "") -> None:
            names = [""] + [g["name"] for g in self.app.db.list_client_groups()]
            group_menu.configure(values=names)
            group_var.set(select if select in names else "")

        def note(text: str) -> None:
            msg.configure(text=text)

        def add_group() -> None:
            name = name_var.get().strip()
            if not name:
                note("Enter a group name.")
                return
            try:
                self.app.db.add_client_group(name)
            except Exception as exc:
                note(str(exc))
                return
            name_var.set("")
            refresh_menu(name)
            note(f"Added: {name}")
            self.refresh()

        def rename_group() -> None:
            old = group_var.get().strip()
            new = name_var.get().strip()
            if not old or not new:
                note("Select a group and enter the new name.")
                return
            try:
                self.app.db.update_client_group(id_map()[old], new)
            except Exception as exc:
                note(str(exc))
                return
            name_var.set("")
            refresh_menu(new)
            note(f"Renamed to: {new}")
            self.refresh()

        def delete_group() -> None:
            old = group_var.get().strip()
            if not old:
                note("Select a group first.")
                return
            if not messagebox.askyesno(
                "Delete group",
                f"Delete group '{old}'? Its clients become ungrouped (not deleted).\n\n"
                "Groups are this PC only — not synced.",
                parent=top,
            ):
                return
            try:
                self.app.db.delete_client_group(id_map()[old])
            except Exception as exc:
                note(str(exc))
                return
            refresh_menu("")
            note(f"Deleted: {old}")
            self.refresh()

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        ctk.CTkButton(btns, text="Add", width=80, command=add_group).pack(side="left")
        ctk.CTkButton(
            btns,
            text="Rename",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=rename_group,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            btns,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=delete_group,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(btns, text="Close", width=80, command=top.destroy).pack(side="right")

        refresh_menu()

    def _open_client_dialog(self) -> None:
        client_id = self._selected_client_id()
        current = self.app.db.get_client(client_id) if client_id is not None else None
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("Edit client" if current else "Add client")
        top.resizable(False, False)
        top.geometry("460x420")
        top.update_idletasks()
        width, height = 460, 420
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
        ctk.CTkLabel(body, text="Group", anchor="w").grid(row=4, column=0, sticky="w", padx=(0, 10), pady=6)
        groups = self.app.db.list_client_groups()
        group_names = ["(No group)"] + [g["name"] for g in groups]
        current_gid = (current or {}).get("group_id")
        current_gname = next((g["name"] for g in groups if g["id"] == current_gid), "(No group)")
        group_var = ctk.StringVar(value=current_gname if current_gname in group_names else "(No group)")
        group_menu = ctk.CTkOptionMenu(body, values=group_names, variable=group_var)
        group_menu.grid(row=4, column=1, sticky="ew", pady=6)
        ctk.CTkLabel(
            body,
            text="Groups are this PC only — not synced.",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 4))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ctk.CTkButton(
            buttons,
            text="Save",
            width=100,
            command=lambda: self._save_client_dialog(
                top,
                client_id,
                name_var,
                contact_var,
                email_var,
                status_var,
                group_var,
                {g["name"]: g["id"] for g in groups},
            ),
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
        self,
        top,
        client_id: int | None,
        name_var,
        contact_var,
        email_var,
        status_var,
        group_var=None,
        group_map: dict | None = None,
    ) -> None:
        name = name_var.get().strip()
        if not name:
            self.feedback.error("Enter a company name.")
            return
        contact = contact_var.get().strip()
        email = email_var.get().strip()
        status = "active" if status_var.get() == "Active" else "inactive"
        group_name = (group_var.get() if group_var is not None else "(No group)").strip()
        group_id = (group_map or {}).get(group_name)
        clear_group = group_id is None
        try:
            from skyadmin_pro.services.client_commands import AddClientCommand, EditClientCommand

            if client_id is None:
                self._undo.execute(
                    AddClientCommand(
                        self.app.db,
                        name=name,
                        contact=contact,
                        email=email,
                        status=status,
                        group_id=group_id,
                        clear_group=clear_group,
                    )
                )
                view = self.app.get_view("database_tasks")
                if view is not None and getattr(view, "tasks_panel", None) is not None:
                    view.tasks_panel.refresh()
            else:
                self._undo.execute(
                    EditClientCommand(
                        self.app.db,
                        client_id,
                        name=name,
                        contact_name=contact,
                        email=email,
                        status=status,
                        group_id=group_id,
                        clear_group=clear_group,
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
        conflicts = self._undo.preview_conflicts()
        force = False
        if conflicts:
            from tkinter import messagebox

            if not messagebox.askyesno(
                "Undo will overwrite",
                "Undoing would overwrite rows created after the delete:\n\n"
                + "\n".join(f"• {c}" for c in conflicts)
                + "\n\nOverwrite them?",
                parent=self.winfo_toplevel(),
            ):
                return
            force = True
        try:
            label = self._undo.undo(force=force)
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

    def _on_client_tree_select(self, _event=None) -> None:
        if not hasattr(self, "_batch_selection_label"):
            return
        count = len(self.client_tree.selected_iids())
        if count > 0:
            self._batch_selection_label.configure(
                text=f"{count} selected",
                text_color=("#0284c7", "#38bdf8"),
            )
        else:
            self._batch_selection_label.configure(
                text="0 selected",
                text_color=TEXT_MUTED,
            )

    def _batch_delete(self) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        if not messagebox.askyesno(
            "Batch delete",
            f"Permanently delete {len(iids)} selected client(s)?\n\n"
            "This cannot be undone after leaving this screen (Ctrl+Z works once). "
            "Prefer Archive to soft-delete instead.",
            parent=self.winfo_toplevel(),
        ):
            return
        from skyadmin_pro.services.client_commands import DeleteClientsCommand

        ids = [int(iid) for iid in iids]
        count = self._undo.execute(DeleteClientsCommand(self.app.db, ids))
        self.feedback.success(f"Deleted {count} client(s). (Ctrl+Z to undo)")
        self.refresh()

    def _batch_archive(self) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        if not messagebox.askyesno(
            "Archive clients",
            f"Archive {len(iids)} selected client(s)?\n\n"
            "They are hidden from the company list (soft-delete). "
            "You can undo once with Ctrl+Z.",
            parent=self.winfo_toplevel(),
        ):
            return
        from skyadmin_pro.services.client_commands import ArchiveClientsCommand

        ids = [int(iid) for iid in iids]
        count = self._undo.execute(ArchiveClientsCommand(self.app.db, ids))
        self.feedback.success(f"Archived {count} client(s). (Ctrl+Z to undo)")
        self.refresh()

    def _batch_set_status(self, status: str) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        from skyadmin_pro.services.client_commands import SetStatusCommand

        ids = [int(iid) for iid in iids]
        count = self._undo.execute(SetStatusCommand(self.app.db, ids, status))
        label = "Active" if status.lower() == "active" else "Inactive"
        self.feedback.success(f"Updated {count} client(s) to {label}.")
        self.refresh()

    def _batch_assign_group(self) -> None:
        iids = self.client_tree.selected_iids()
        if not iids:
            self.feedback.error("Select one or more clients first.")
            return
        groups = self.app.db.list_client_groups()
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title("Assign group")
        top.resizable(False, False)
        top.geometry("360x220")
        make_modal(top)
        body = ctk.CTkFrame(top, corner_radius=CARD_RADIUS)
        body.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            body,
            text=f"Assign {len(iids)} selected client(s) to a group.",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkLabel(
            body,
            text="Groups are this PC only — not synced.",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))
        group_names = ["(No group)"] + [g["name"] for g in groups]
        group_var = ctk.StringVar(value="(No group)")
        ctk.CTkOptionMenu(body, values=group_names, variable=group_var, width=280).grid(
            row=2, column=0, sticky="ew", pady=(0, 12)
        )
        group_map = {g["name"]: g["id"] for g in groups}

        def apply() -> None:
            from skyadmin_pro.services.client_commands import AssignGroupCommand

            name = group_var.get().strip()
            gid = group_map.get(name)  # None for "(No group)"
            ids = [int(iid) for iid in iids]
            count = self._undo.execute(AssignGroupCommand(self.app.db, ids, gid))
            top.destroy()
            label = name if gid is not None else "no group"
            self.feedback.success(f"Assigned {count} client(s) to {label}.")
            self.refresh()

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew")
        ctk.CTkButton(btns, text="Assign", width=100, command=apply).pack(side="right")
        ctk.CTkButton(
            btns,
            text="Cancel",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=top.destroy,
        ).pack(side="right", padx=(0, 8))

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
