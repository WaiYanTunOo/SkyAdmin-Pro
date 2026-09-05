"""Office Hub — vault tab."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import CLIENT_CREDENTIAL_TYPES, OFFICE_SYSTEM_TYPES
from skyadmin_pro.services.workflow import copy_to_clipboard
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import themed_entry, themed_tabview


class VaultTabMixin:
    def _build_passwords_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        pw_tabs = themed_tabview(parent)
        pw_tabs.grid(row=0, column=0, sticky="nsew", padx=4, pady=8)
        pw_tabs.add("Client DBD / RD")
        pw_tabs.add("Office accounts")
        self._password_subtabs = pw_tabs
        self._build_client_credentials_tab(pw_tabs.tab("Client DBD / RD"))
        self._build_office_credentials_tab(pw_tabs.tab("Office accounts"))

    def _build_client_credentials_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(4, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.client_cred_search_var = ctk.StringVar()
        themed_entry(
            toolbar, textvariable=self.client_cred_search_var, placeholder_text="Search client, DBD/RD no…"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.client_cred_search_var.trace_add("write", debounced_after(self, self._refresh_client_credentials))
        self.client_cred_type_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["All"] + list(CLIENT_CREDENTIAL_TYPES),
            command=lambda _v: self._refresh_client_credentials(),
            width=130,
        )
        self.client_cred_type_menu.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="New", width=70, command=self._new_client_credential).grid(row=0, column=2)

        self.client_cred_tree = ThemedTreeview(
            parent,
            columns=(
                ("client", "Client", 160),
                ("type", "Type", 80),
                ("login", "Login ID", 180),
                ("portal", "Portal", 140),
            ),
            on_select=self._on_client_cred_select,
            showheight=7,
        )
        self.client_cred_tree.grid(row=1, column=0, sticky="nsew")

        form = ctk.CTkFrame(parent, corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", pady=(8, 4))
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(
            form,
            text="Client portal login (encrypted)",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(10, 6))

        self.cc_client = ctk.StringVar()
        self.cc_type = ctk.StringVar(value=CLIENT_CREDENTIAL_TYPES[0])
        self.cc_login_id = ctk.StringVar()
        self.cc_password = ctk.StringVar()
        self.cc_url = ctk.StringVar()
        self.cc_favorite = ctk.BooleanVar()
        self.cc_pw_entry: ctk.CTkEntry | None = None

        self.cc_client_menu = ctk.CTkComboBox(form, variable=self.cc_client, values=[""], width=220)
        fields = [
            ("Client company", self.cc_client_menu, 1, 0, "widget", None),
            ("Type", self.cc_type, 1, 2, "menu", CLIENT_CREDENTIAL_TYPES),
            ("Login ID / username / email", self.cc_login_id, 2, 0, "entry", None),
            ("Portal URL", self.cc_url, 2, 2, "entry", None),
        ]
        for label, var, row, col, kind, values in fields:
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=row, column=col, sticky="w", padx=16, pady=4)
            if kind == "menu":
                ctk.CTkOptionMenu(form, variable=var, values=list(values or ()), width=180).grid(
                    row=row, column=col + 1, sticky="w", padx=(0, 16), pady=4
                )
            elif kind == "widget":
                var.grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)
            else:
                themed_entry(form, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Password", anchor="w").grid(row=3, column=0, sticky="w", padx=16, pady=4)
        pw_row = ctk.CTkFrame(form, fg_color="transparent")
        pw_row.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        pw_row.grid_columnconfigure(0, weight=1)
        self.cc_pw_entry = themed_entry(pw_row, textvariable=self.cc_password, show="*")
        self.cc_pw_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(pw_row, text="Show", width=64, command=self._toggle_client_pw).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(pw_row, text="Copy", width=64, command=self._copy_client_pw).grid(row=0, column=2, padx=(8, 0))

        ctk.CTkLabel(form, text="Notes", anchor="w").grid(row=4, column=0, sticky="nw", padx=16, pady=4)
        self.cc_notes_box = ctk.CTkTextbox(form, height=50)
        self.cc_notes_box.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkCheckBox(form, text="Favorite", variable=self.cc_favorite).grid(row=5, column=1, sticky="w")

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 12))
        ctk.CTkButton(buttons, text="Save", width=90, command=self._save_client_credential).pack(side="left")
        ctk.CTkButton(
            buttons,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._delete_client_credential,
        ).pack(side="left", padx=(8, 0))

    def _build_office_credentials_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(4, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.office_cred_search_var = ctk.StringVar()
        themed_entry(
            toolbar, textvariable=self.office_cred_search_var, placeholder_text="Search office accounts…"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.office_cred_search_var.trace_add("write", debounced_after(self, self._refresh_office_credentials))
        self.office_cred_type_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["All"] + list(OFFICE_SYSTEM_TYPES),
            command=lambda _v: self._refresh_office_credentials(),
            width=120,
        )
        self.office_cred_type_menu.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="New", width=70, command=self._new_office_credential).grid(row=0, column=2)

        self.office_cred_tree = ThemedTreeview(
            parent,
            columns=(
                ("label", "Account", 180),
                ("login", "Username / email", 180),
                ("type", "System", 100),
                ("contact", "Contact", 120),
            ),
            on_select=self._on_office_cred_select,
            showheight=7,
        )
        self.office_cred_tree.grid(row=1, column=0, sticky="nsew")

        form = ctk.CTkFrame(parent, corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", pady=(8, 4))
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(
            form,
            text="Office username / email (encrypted)",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(10, 6))

        self.oc_label = ctk.StringVar()
        self.oc_login = ctk.StringVar()
        self.oc_email = ctk.StringVar()
        self.oc_password = ctk.StringVar()
        self.oc_type = ctk.StringVar(value=OFFICE_SYSTEM_TYPES[0])
        self.oc_url = ctk.StringVar()
        self.oc_contact = ctk.StringVar()
        self.oc_favorite = ctk.BooleanVar()
        self.oc_pw_entry: ctk.CTkEntry | None = None

        office_fields = [
            ("Account label", self.oc_label, 1, 0),
            ("Username", self.oc_login, 1, 2),
            ("Email", self.oc_email, 2, 0),
            ("System type", self.oc_type, 2, 2, True),
            ("Portal URL", self.oc_url, 3, 0),
            ("Linked contact", self.oc_contact, 3, 2),
        ]
        for item in office_fields:
            label, var, row, col = item[:4]
            is_menu = len(item) > 4 and item[4]
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=row, column=col, sticky="w", padx=16, pady=4)
            if is_menu:
                ctk.CTkOptionMenu(form, variable=var, values=list(OFFICE_SYSTEM_TYPES), width=180).grid(
                    row=row, column=col + 1, sticky="w", padx=(0, 16), pady=4
                )
            else:
                themed_entry(form, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Password", anchor="w").grid(row=4, column=0, sticky="w", padx=16, pady=4)
        pw_row = ctk.CTkFrame(form, fg_color="transparent")
        pw_row.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        pw_row.grid_columnconfigure(0, weight=1)
        self.oc_pw_entry = themed_entry(pw_row, textvariable=self.oc_password, show="*")
        self.oc_pw_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(pw_row, text="Show", width=64, command=self._toggle_office_pw).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(pw_row, text="Copy", width=64, command=self._copy_office_pw).grid(row=0, column=2, padx=(8, 0))

        ctk.CTkLabel(form, text="Notes", anchor="w").grid(row=5, column=0, sticky="nw", padx=16, pady=4)
        self.oc_notes_box = ctk.CTkTextbox(form, height=50)
        self.oc_notes_box.grid(row=5, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkCheckBox(form, text="Favorite", variable=self.oc_favorite).grid(row=6, column=1, sticky="w")

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=7, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 12))
        ctk.CTkButton(buttons, text="Save", width=90, command=self._save_office_credential).pack(side="left")
        ctk.CTkButton(
            buttons,
            text="Delete",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._delete_office_credential,
        ).pack(side="left", padx=(8, 0))

    def _refresh_client_credentials(self) -> None:
        if "Passwords" not in self._lazy_tabs:
            return
        cred_type = self.client_cred_type_menu.get()
        ctype = None if cred_type == "All" else cred_type
        rows = self.app.db.list_client_credentials(query=self.client_cred_search_var.get(), credential_type=ctype)
        tree_rows = [
            (
                row.get("client_name") or "",
                row.get("credential_type") or "",
                row.get("login_id") or row.get("username") or row.get("registration_number") or "",
                row.get("portal_url") or "",
            )
            for row in rows
        ]
        self.client_cred_tree.set_rows(
            tree_rows,
            iids=[str(r["id"]) for r in rows],
            empty_message="No client portal logins match this filter.",
        )

    def _on_client_cred_select(self, iid: str | None) -> None:
        if not iid:
            return
        self._selected_client_cred_id = int(iid)
        row = self.app.db.get_client_credential(self._selected_client_cred_id)
        if not row:
            return
        self.cc_client.set(row.get("client_name") or "")
        self.cc_type.set(row.get("credential_type") or CLIENT_CREDENTIAL_TYPES[0])
        self.cc_login_id.set(row.get("login_id") or row.get("username") or row.get("registration_number") or "")
        self.cc_password.set(row.get("password") or "")
        self.cc_url.set(row.get("portal_url") or "")
        self.cc_favorite.set(bool(row.get("is_favorite")))
        self.cc_notes_box.delete("1.0", "end")
        self.cc_notes_box.insert("1.0", row.get("notes") or "")

    def _new_client_credential(self) -> None:
        self._selected_client_cred_id = None
        self.cc_client.set("")
        self.cc_type.set(CLIENT_CREDENTIAL_TYPES[0])
        self.cc_login_id.set("")
        self.cc_password.set("")
        self.cc_url.set("")
        self.cc_favorite.set(False)
        self.cc_notes_box.delete("1.0", "end")

    def _save_client_credential(self) -> None:
        client_id = self._client_id(self.cc_client.get())
        if client_id is None:
            self.feedback.error("Select a valid client company name.")
            return
        payload = {
            "client_id": client_id,
            "credential_type": self.cc_type.get(),
            "login_id": self.cc_login_id.get().strip() or None,
            "password": self.cc_password.get(),
            "portal_url": self.cc_url.get().strip() or None,
            "notes": self.cc_notes_box.get("1.0", "end").strip() or None,
            "is_favorite": self.cc_favorite.get(),
        }
        if self._selected_client_cred_id is not None and not payload["password"]:
            payload.pop("password", None)
        try:
            if self._selected_client_cred_id is None:
                self._selected_client_cred_id = self.app.db.add_client_credential(**payload)
            else:
                self.app.db.update_client_credential(self._selected_client_cred_id, **payload)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Client credential saved (encrypted).")
        self._refresh_client_credentials()

    def _delete_client_credential(self) -> None:
        if self._selected_client_cred_id is None:
            self.feedback.error("Select a client credential first.")
            return
        if not messagebox.askyesno("Delete", "Delete this client credential?", parent=self.winfo_toplevel()):
            return
        self.app.db.delete_client_credential(self._selected_client_cred_id)
        self._new_client_credential()
        self.feedback.success("Client credential deleted.")
        self._refresh_client_credentials()

    def _toggle_client_pw(self) -> None:
        if self.cc_pw_entry is None:
            return
        self._client_pw_visible = not self._client_pw_visible
        self.cc_pw_entry.configure(show="" if self._client_pw_visible else "*")

    def _copy_client_pw(self) -> None:
        if not self.cc_password.get():
            self.feedback.error("No password to copy.")
            return
        copy_to_clipboard(self.cc_password.get())
        self.feedback.success("Password copied.")

    # Office credentials CRUD ------------------------------------------------

    def _refresh_office_credentials(self) -> None:
        if "Passwords" not in self._lazy_tabs:
            return
        system = self.office_cred_type_menu.get()
        stype = None if system == "All" else system
        rows = self.app.db.list_office_credentials(query=self.office_cred_search_var.get(), system_type=stype)
        tree_rows = [
            (
                row.get("account_label") or "",
                row.get("login_id") or row.get("email") or "",
                row.get("system_type") or "",
                row.get("contact_name") or "",
            )
            for row in rows
        ]
        self.office_cred_tree.set_rows(
            tree_rows,
            iids=[str(r["id"]) for r in rows],
            empty_message="No office accounts match this filter.",
        )

    def _on_office_cred_select(self, iid: str | None) -> None:
        if not iid:
            return
        self._selected_office_cred_id = int(iid)
        row = self.app.db.get_office_credential(self._selected_office_cred_id)
        if not row:
            return
        self.oc_label.set(row.get("account_label") or "")
        self.oc_login.set(row.get("login_id") or "")
        self.oc_email.set(row.get("email") or "")
        self.oc_password.set(row.get("password") or "")
        self.oc_type.set(row.get("system_type") or OFFICE_SYSTEM_TYPES[0])
        self.oc_url.set(row.get("portal_url") or "")
        self.oc_contact.set(row.get("contact_name") or "")
        self.oc_favorite.set(bool(row.get("is_favorite")))
        self.oc_notes_box.delete("1.0", "end")
        self.oc_notes_box.insert("1.0", row.get("notes") or "")

    def _new_office_credential(self) -> None:
        self._selected_office_cred_id = None
        self.oc_label.set("")
        self.oc_login.set("")
        self.oc_email.set("")
        self.oc_password.set("")
        self.oc_type.set(OFFICE_SYSTEM_TYPES[0])
        self.oc_url.set("")
        self.oc_contact.set("")
        self.oc_favorite.set(False)
        self.oc_notes_box.delete("1.0", "end")

    def _save_office_credential(self) -> None:
        payload = {
            "account_label": self.oc_label.get(),
            "login_id": self.oc_login.get().strip() or None,
            "email": self.oc_email.get().strip() or None,
            "password": self.oc_password.get(),
            "system_type": self.oc_type.get(),
            "portal_url": self.oc_url.get().strip() or None,
            "contact_id": self._contact_id(self.oc_contact.get()),
            "notes": self.oc_notes_box.get("1.0", "end").strip() or None,
            "is_favorite": self.oc_favorite.get(),
        }
        try:
            if self._selected_office_cred_id is None:
                self._selected_office_cred_id = self.app.db.add_office_credential(**payload)
            else:
                self.app.db.update_office_credential(self._selected_office_cred_id, **payload)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Office account saved (encrypted).")
        self._refresh_office_credentials()

    def _delete_office_credential(self) -> None:
        if self._selected_office_cred_id is None:
            self.feedback.error("Select an office account first.")
            return
        if not messagebox.askyesno("Delete", "Delete this office account?", parent=self.winfo_toplevel()):
            return
        self.app.db.delete_office_credential(self._selected_office_cred_id)
        self._new_office_credential()
        self.feedback.success("Office account deleted.")
        self._refresh_office_credentials()

    def _toggle_office_pw(self) -> None:
        if self.oc_pw_entry is None:
            return
        self._office_pw_visible = not self._office_pw_visible
        self.oc_pw_entry.configure(show="" if self._office_pw_visible else "*")

    def _copy_office_pw(self) -> None:
        if not self.oc_password.get():
            self.feedback.error("No password to copy.")
            return
        copy_to_clipboard(self.oc_password.get())
        self.feedback.success("Password copied.")
