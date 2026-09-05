"""Office Hub — contacts tab."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import CONTACT_CATEGORIES
from skyadmin_pro.services.workflow import copy_to_clipboard
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry


class ContactsTabMixin:
    def _build_contacts_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(8, 8))
        toolbar.grid_columnconfigure(1, weight=1)
        self.contact_search_var = ctk.StringVar()
        themed_entry(toolbar, textvariable=self.contact_search_var, placeholder_text="Search contacts…").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=(0, 8)
        )
        self.contact_search_var.trace_add("write", debounced_after(self, self._refresh_contacts))
        self.contact_category_menu = ctk.CTkOptionMenu(
            toolbar, values=["All"] + list(CONTACT_CATEGORIES), command=lambda _v: self._refresh_contacts(), width=150
        )
        self.contact_category_menu.grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(toolbar, text="New contact", width=110, command=self._new_contact).grid(row=0, column=3)

        self.contacts_tree = ThemedTreeview(
            parent,
            columns=(
                ("name", "Name", 180),
                ("organization", "Company", 160),
                ("role", "Role", 120),
                ("phone", "Phone", 110),
                ("category", "Category", 100),
            ),
            on_select=self._on_contact_select,
            showheight=8,
        )
        self.contacts_tree.grid(row=1, column=0, sticky="nsew")

        form = ctk.CTkFrame(parent, corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", pady=(10, 8))
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(form, text="Contact details", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12, 8)
        )
        self.c_name = ctk.StringVar()
        self.c_role = ctk.StringVar()
        self.c_org = ctk.StringVar()
        self.c_dept = ctk.StringVar()
        self.c_phone = ctk.StringVar()
        self.c_email = ctk.StringVar()
        self.c_line = ctk.StringVar()
        self.c_category = ctk.StringVar(value=CONTACT_CATEGORIES[0])
        self.c_client = ctk.StringVar()
        self.c_favorite = ctk.BooleanVar()

        self.c_org_menu = ctk.CTkComboBox(form, variable=self.c_org, values=[""], width=220)
        self.c_dept_menu = ctk.CTkComboBox(form, variable=self.c_dept, values=[""], width=220)
        self.c_client_menu = ctk.CTkComboBox(form, variable=self.c_client, values=[""], width=220)

        simple_fields = [
            ("Name", self.c_name, 1, 0),
            ("Role", self.c_role, 1, 2),
            ("Phone", self.c_phone, 3, 0),
            ("Email", self.c_email, 3, 2),
            ("LINE ID", self.c_line, 4, 0),
        ]
        for label, var, row, col in simple_fields:
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=row, column=col, sticky="w", padx=16, pady=4)
            themed_entry(form, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Company", anchor="w").grid(row=2, column=0, sticky="w", padx=16, pady=4)
        self.c_org_menu.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkLabel(form, text="Department", anchor="w").grid(row=2, column=2, sticky="w", padx=16, pady=4)
        self.c_dept_menu.grid(row=2, column=3, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Category", anchor="w").grid(row=4, column=2, sticky="w", padx=16, pady=4)
        ctk.CTkOptionMenu(form, variable=self.c_category, values=list(CONTACT_CATEGORIES), width=180).grid(
            row=4, column=3, sticky="w", padx=(0, 16), pady=4
        )
        ctk.CTkLabel(form, text="Linked client", anchor="w").grid(row=5, column=0, sticky="w", padx=16, pady=4)
        self.c_client_menu.grid(row=5, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Notes", anchor="w").grid(row=6, column=0, sticky="nw", padx=16, pady=4)
        self.c_notes_box = ctk.CTkTextbox(form, height=70)
        self.c_notes_box.grid(row=6, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkCheckBox(form, text="Favorite", variable=self.c_favorite).grid(row=7, column=1, sticky="w", pady=4)

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=8, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 14))
        ctk.CTkButton(buttons, text="Save contact", width=120, command=self._save_contact).pack(side="left")
        ctk.CTkButton(
            buttons, text="Delete", width=90, fg_color="transparent", border_width=1, command=self._delete_contact
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            buttons,
            text="Copy phone",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._copy_contact_phone,
        ).pack(side="left", padx=(8, 0))

    def _refresh_contact_pickers(self) -> None:
        companies = [""] + self.app.db.list_organizations()
        depts = [""] + self.app.db.list_departments()
        clients = [""] + self.app.db.list_client_names()
        self.c_org_menu.configure(values=companies)
        self.c_dept_menu.configure(values=depts)
        self.c_client_menu.configure(values=clients)

    def _refresh_contacts(self) -> None:
        if "Contacts" not in self._lazy_tabs:
            return
        cat = self.contact_category_menu.get()
        category = None if cat == "All" else cat
        rows = self.app.db.list_office_contacts(query=self.contact_search_var.get(), category=category)
        tree_rows = [
            (
                row.get("name") or "",
                row.get("organization") or "",
                row.get("role_title") or "",
                row.get("phone") or "",
                row.get("category") or "",
            )
            for row in rows
        ]
        self.contacts_tree.set_rows(
            tree_rows,
            iids=[str(r["id"]) for r in rows],
            empty_message="No contacts match this search.",
        )

    def _on_contact_select(self, iid: str | None) -> None:
        if not iid:
            return
        self._selected_contact_id = int(iid)
        row = self.app.db.get_office_contact(self._selected_contact_id)
        if not row:
            return
        self.c_name.set(row.get("name") or "")
        self.c_role.set(row.get("role_title") or "")
        self.c_org.set(row.get("organization") or "")
        self.c_dept.set(row.get("department") or "")
        self.c_phone.set(row.get("phone") or "")
        self.c_email.set(row.get("email") or "")
        self.c_line.set(row.get("line_id") or "")
        self.c_category.set(row.get("category") or CONTACT_CATEGORIES[0])
        self.c_client.set(row.get("client_name") or "")
        self.c_favorite.set(bool(row.get("is_favorite")))
        self.c_notes_box.delete("1.0", "end")
        self.c_notes_box.insert("1.0", row.get("notes") or "")

    def _new_contact(self) -> None:
        self._selected_contact_id = None
        self.c_name.set("")
        self.c_role.set("")
        self.c_org.set("")
        self.c_dept.set("")
        self.c_phone.set("")
        self.c_email.set("")
        self.c_line.set("")
        self.c_category.set(CONTACT_CATEGORIES[0])
        self.c_client.set("")
        self.c_favorite.set(False)
        self.c_notes_box.delete("1.0", "end")

    def _save_contact(self) -> None:
        client_name = self.c_client.get().strip()
        client_id = self._client_id(client_name) if client_name else None
        if client_name and client_id is None:
            self.feedback.error("Select a valid linked client from the list, or leave blank.")
            return
        org = self.c_org.get().strip() or None
        dept = self.c_dept.get().strip() or None
        if not org and client_name:
            org = client_name
            self.c_org.set(org)
        self.app.db.ensure_directory_entries(organization=org, department=dept)
        self._refresh_contact_pickers()
        payload = {
            "name": self.c_name.get(),
            "role_title": self.c_role.get().strip() or None,
            "organization": org,
            "department": dept,
            "phone": self.c_phone.get().strip() or None,
            "email": self.c_email.get().strip() or None,
            "line_id": self.c_line.get().strip() or None,
            "category": self.c_category.get(),
            "client_id": client_id,
            "notes": self.c_notes_box.get("1.0", "end").strip() or None,
            "is_favorite": self.c_favorite.get(),
        }
        try:
            if self._selected_contact_id is None:
                self._selected_contact_id = self.app.db.add_office_contact(**payload)
            else:
                self.app.db.update_office_contact(self._selected_contact_id, **payload)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Contact saved.")
        self._refresh_contacts()

    def _delete_contact(self) -> None:
        if self._selected_contact_id is None:
            self.feedback.error("Select a contact first.")
            return
        if not messagebox.askyesno("Delete contact", "Delete this contact?", parent=self.winfo_toplevel()):
            return
        self.app.db.delete_office_contact(self._selected_contact_id)
        self._new_contact()
        self.feedback.success("Contact deleted.")
        self._refresh_contacts()

    def _copy_contact_phone(self) -> None:
        phone = self.c_phone.get().strip()
        if not phone:
            self.feedback.error("No phone number to copy.")
            return
        copy_to_clipboard(phone)
        self.feedback.success("Phone copied.")
