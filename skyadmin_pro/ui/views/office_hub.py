"""Office Hub — contacts directory, password vault, and work notebook."""

from __future__ import annotations

from datetime import date, timedelta
from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    CLIENT_CREDENTIAL_TYPES,
    CONTACT_CATEGORIES,
    NOTEBOOK_ENTRY_TYPES,
    OFFICE_SYSTEM_TYPES,
)
from skyadmin_pro.services.office_hub_rollout import (
    list_office_setup_rows,
    migrate_legacy_ird_passwords,
    seed_liaison_contacts,
)
from skyadmin_pro.services.workflow import copy_to_clipboard
from skyadmin_pro.ui.debounce import debounced_after
from skyadmin_pro.ui.setup_rollout import RolloutAction, SetupRolloutPanel
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_entry, themed_textbox


class OfficeHubView(BaseView):
    title = "Office Hub"
    subtitle = (
        "Office contacts, client DBD/RD passwords, office account vault, and daily/weekly notebook for instructions."
    )

    def build(self) -> None:
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)
        self.feedback = FeedbackLabel(self.body)
        self.feedback.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self._lazy_tabs: set[str] = set()
        self.tabs = ctk.CTkTabview(self.body, command=self._on_tab_changed)
        self.tabs.grid(row=0, column=0, sticky="nsew")
        for name in ("Setup", "Contacts", "Passwords", "Notebook"):
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self._selected_contact_id: int | None = None
        self._selected_client_cred_id: int | None = None
        self._selected_office_cred_id: int | None = None
        self._selected_note_id: int | None = None
        self._client_pw_visible = False
        self._office_pw_visible = False

        self._build_setup_tab(self.tabs.tab("Setup"))
        self._lazy_tabs.add("Setup")

    # ------------------------------------------------------------------ #
    # Setup — Wave D migration queue
    # ------------------------------------------------------------------ #

    def _build_setup_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self._office_setup_panel = SetupRolloutPanel(
            parent,
            title="Office Hub rollout — contacts & portal logins per client",
            description=(
                "Import director contacts from Company Details, migrate legacy IRD passwords "
                "to Client DBD/RD, then add DBD/RD portal logins per company."
            ),
            columns=(
                ("company", "Company", 220),
                ("status", "Setup", 90),
                ("contacts", "Contacts", 80),
                ("logins", "Portal logins", 100),
                ("missing", "Missing", 220),
                ("director", "Director / contact", 180),
            ),
            actions=(
                RolloutAction("Open portal logins", self._open_selected_office_credentials, width=140),
                RolloutAction("Open contacts", self._open_selected_office_contacts, width=120),
                RolloutAction("Import liaison contact", self._import_selected_liaison_contact, width=160),
                RolloutAction(
                    "Import all liaisons",
                    self._import_all_liaison_contacts,
                    width=140,
                    fg_color="transparent",
                    border_width=1,
                ),
                RolloutAction(
                    "Migrate legacy IRD",
                    self._migrate_all_legacy_ird,
                    width=140,
                    fg_color="transparent",
                    border_width=1,
                ),
            ),
            on_double_click=self._open_selected_office_credentials,
            showheight=12,
            use_card=False,
            tree_sticky="nsew",
            tree_row_weight=1,
        )
        self._office_setup_panel.grid(row=0, column=0, sticky="nsew")
        self._office_setup_panel.configure_data(
            list_rows=lambda: list_office_setup_rows(self.app.db),
            row_cells=self._office_setup_cells,
            summary=lambda ready, total: f"{ready} of {total} client(s) have contacts and portal logins",
        )

    def _office_setup_cells(self, row: dict) -> tuple:
        missing = ", ".join(row.get("setup_missing") or []) or "—"
        director = row.get("director") or row.get("contact_name") or "—"
        return (
            row.get("name") or "",
            row.get("setup_status") or "",
            str(int(row.get("contact_count") or 0)),
            str(int(row.get("credential_count") or 0)),
            missing,
            director,
        )

    def refresh_setup(self) -> None:
        if hasattr(self, "_office_setup_panel"):
            self._office_setup_panel.refresh()

    def _selected_office_setup_row(self) -> dict | None:
        if not hasattr(self, "_office_setup_panel"):
            return None
        return self._office_setup_panel.selected_row()

    def _open_selected_office_credentials(self, _iid: str | None = None) -> None:
        row = self._selected_office_setup_row()
        if not row:
            self.feedback.error("Select a client first.")
            return
        self.focus_client_credentials((row.get("name") or "").strip())

    def _open_selected_office_contacts(self) -> None:
        row = self._selected_office_setup_row()
        if not row:
            self.feedback.error("Select a client first.")
            return
        name = (row.get("name") or "").strip()
        self._ensure_tab("Contacts")
        self.tabs.set("Contacts")
        self.contact_search_var.set(name)
        self._refresh_contacts()

    def _import_selected_liaison_contact(self) -> None:
        row = self._selected_office_setup_row()
        if not row:
            self.feedback.error("Select a client first.")
            return
        if not row.get("can_seed_contact"):
            self.feedback.error("No director/contact name on file to import.")
            return
        created = self.app.db.seed_client_liaison_contacts(only_missing=True, client_id=int(row["id"]))
        if created:
            self.feedback.success("Liaison contact imported.")
        else:
            self.feedback.info("Contact already exists or nothing to import.")
        self.refresh_setup()
        self._refresh_contacts()

    def _import_all_liaison_contacts(self) -> None:
        pending = sum(1 for row in list_office_setup_rows(self.app.db) if row.get("can_seed_contact"))
        if pending == 0:
            self.feedback.info("No clients need liaison contact import.")
            return
        if not messagebox.askyesno(
            "Import liaison contacts",
            f"Create Client liaison contacts for {pending} client(s) from Company Details?",
            parent=self.winfo_toplevel(),
        ):
            return
        created = seed_liaison_contacts(self.app.db, only_missing=True)
        self.feedback.success(f"Imported {created} liaison contact(s).")
        self.refresh_setup()
        self._refresh_contacts()

    def _migrate_all_legacy_ird(self) -> None:
        pending = sum(
            1 for row in list_office_setup_rows(self.app.db) if "IRD migrate" in (row.get("setup_missing") or [])
        )
        if pending == 0:
            self.feedback.info("No legacy IRD passwords need migration.")
            return
        if not messagebox.askyesno(
            "Migrate IRD passwords",
            f"Import {pending} legacy IRD password(s) into Office Hub RD credentials?",
            parent=self.winfo_toplevel(),
        ):
            return
        migrated = migrate_legacy_ird_passwords(self.app.db)
        self.feedback.success(f"Migrated {migrated} IRD password(s).")
        self.refresh_setup()
        self._refresh_client_credentials()

    def open_setup(self) -> None:
        self.tabs.set("Setup")
        self.refresh_setup()

    # ------------------------------------------------------------------ #
    # Contacts
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Passwords — client credentials + office accounts (separate tables)
    # ------------------------------------------------------------------ #

    def _build_passwords_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        pw_tabs = ctk.CTkTabview(parent)
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

    # ------------------------------------------------------------------ #
    # Notebook
    # ------------------------------------------------------------------ #

    def _build_notebook_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(8, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        self.note_search_var = ctk.StringVar()
        themed_entry(toolbar, textvariable=self.note_search_var, placeholder_text="Search notebook…").grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        self.note_search_var.trace_add("write", debounced_after(self, self._refresh_notes))
        type_labels = ["All"] + [label for _key, label in NOTEBOOK_ENTRY_TYPES]
        self.note_type_menu = ctk.CTkOptionMenu(
            toolbar, values=type_labels, command=lambda _v: self._refresh_notes(), width=170
        )
        self.note_type_menu.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Today", width=70, command=self._filter_notes_today).grid(
            row=0, column=2, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="This week", width=90, command=self._filter_notes_week).grid(
            row=0, column=3, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="New note", width=100, command=self._new_note).grid(row=0, column=4)

        self.notes_tree = ThemedTreeview(
            parent,
            columns=(
                ("date", "Date", 100),
                ("type", "Type", 130),
                ("title", "Title", 220),
                ("author", "From", 120),
                ("client", "Client", 140),
            ),
            on_select=self._on_note_select,
            showheight=8,
        )
        self.notes_tree.grid(row=1, column=0, sticky="nsew")

        form = ctk.CTkFrame(parent, corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", pady=(10, 8))
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(form, text="Notebook entry", font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12, 8)
        )

        self.n_type = ctk.StringVar(value=NOTEBOOK_ENTRY_TYPES[-1][1])
        self.n_title = ctk.StringVar()
        self.n_date = ctk.StringVar(value=date.today().isoformat())
        self.n_author = ctk.StringVar()
        self.n_client = ctk.StringVar()
        self.n_follow = ctk.StringVar()
        self.n_pinned = ctk.BooleanVar()

        note_fields = [
            ("Type", self.n_type, 1, 0, "menu"),
            ("Title", self.n_title, 1, 2, "entry"),
            ("Date", self.n_date, 2, 0, "entry"),
            ("Author / from", self.n_author, 2, 2, "entry"),
            ("Linked client", self.n_client, 3, 0, "entry"),
            ("Follow-up date", self.n_follow, 3, 2, "entry"),
        ]
        for label, var, row, col, kind in note_fields:
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=row, column=col, sticky="w", padx=16, pady=4)
            if kind == "menu":
                ctk.CTkOptionMenu(form, variable=var, values=[lbl for _k, lbl in NOTEBOOK_ENTRY_TYPES], width=200).grid(
                    row=row, column=col + 1, sticky="w", padx=(0, 16), pady=4
                )
            else:
                themed_entry(form, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)

        ctk.CTkLabel(form, text="Body", anchor="w").grid(row=4, column=0, sticky="nw", padx=16, pady=4)
        self.n_body_box = ctk.CTkTextbox(form, height=120)
        self.n_body_box.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(0, 16), pady=4)
        ctk.CTkCheckBox(form, text="Pin to top", variable=self.n_pinned).grid(row=5, column=1, sticky="w", pady=4)

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=6, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 14))
        ctk.CTkButton(buttons, text="Save note", width=110, command=self._save_note).pack(side="left")
        ctk.CTkButton(
            buttons, text="Delete", width=90, fg_color="transparent", border_width=1, command=self._delete_note
        ).pack(side="left", padx=(8, 0))

        self._note_from_date: str | None = None
        self._note_to_date: str | None = None

    def _ensure_tab(self, name: str) -> None:
        if name in self._lazy_tabs:
            return
        if name == "Contacts":
            self._build_contacts_tab(self.tabs.tab("Contacts"))
        elif name == "Passwords":
            self._build_passwords_tab(self.tabs.tab("Passwords"))
        elif name == "Notebook":
            self._build_notebook_tab(self.tabs.tab("Notebook"))
        self._lazy_tabs.add(name)

    def _on_tab_changed(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = "Setup"
        self._ensure_tab(current)
        self._refresh_active_tab(current)

    def _refresh_active_tab(self, tab_name: str) -> None:
        if tab_name == "Setup":
            self.refresh_setup()
        elif tab_name == "Contacts":
            self._refresh_contact_pickers()
            self._refresh_contacts()
        elif tab_name == "Passwords":
            self._refresh_contact_pickers()
            clients = [""] + self.app.db.list_client_names()
            if hasattr(self, "cc_client_menu"):
                self.cc_client_menu.configure(values=clients)
            self._refresh_client_credentials()
            self._refresh_office_credentials()
        elif tab_name == "Notebook":
            self._refresh_notes()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def on_show(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = "Setup"
        self._ensure_tab(current)
        self._refresh_active_tab(current)
        pending = getattr(self, "_pending_client_credentials", None)
        if pending:
            self._pending_client_credentials = None
            if isinstance(pending, str):
                self.focus_client_credentials(pending)
            else:
                name, cred_type, cred_id = pending
                self.focus_client_credentials(name, credential_type=cred_type, credential_id=cred_id)

    def focus_client_credentials(
        self,
        client_name: str,
        *,
        credential_type: str | None = None,
        credential_id: int | None = None,
    ) -> None:
        """Open Client DBD/RD tab for one client (all types or a specific credential)."""
        clean = (client_name or "").strip()
        if not clean:
            return
        self._ensure_tab("Passwords")
        self.tabs.set("Passwords")
        self._password_subtabs.set("Client DBD / RD")
        type_filter = credential_type if credential_type else "All"
        self.client_cred_type_menu.set(type_filter)
        self.client_cred_search_var.set(clean)
        self.cc_client.set(clean)
        self._refresh_client_credentials()
        client_id = self._client_id(clean)
        rows = self.app.db.list_client_credentials(
            client_id=client_id,
            credential_type=None if type_filter == "All" else type_filter,
        )
        target_id = str(credential_id) if credential_id is not None else None
        if target_id and any(str(row["id"]) == target_id for row in rows):
            pick = target_id
        elif rows:
            pick = str(rows[0]["id"])
        else:
            self._new_client_credential()
            self.cc_client.set(clean)
            if credential_type:
                self.cc_type.set(credential_type)
            return
        self.client_cred_tree.tree.selection_set(pick)
        self.client_cred_tree.tree.focus(pick)
        self._on_client_cred_select(pick)

    def focus_client_rd(self, client_name: str) -> None:
        """Backward-compatible alias — opens RD credentials for the client."""
        self.focus_client_credentials(client_name, credential_type="RD")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _client_id(self, name: str) -> int | None:
        clean = (name or "").strip()
        if not clean:
            return None
        return self.app.db.client_id_by_name(clean)

    def _contact_id(self, name: str) -> int | None:
        clean = (name or "").strip()
        if not clean:
            return None
        for row in self.app.db.list_office_contacts():
            if (row.get("name") or "").lower() == clean.lower():
                return int(row["id"])
        return None

    def _notebook_type_key(self, label: str) -> str | None:
        for key, lbl in NOTEBOOK_ENTRY_TYPES:
            if lbl == label:
                return key
        return None

    def _notebook_type_label(self, key: str) -> str:
        for k, lbl in NOTEBOOK_ENTRY_TYPES:
            if k == key:
                return lbl
        return key

    # Contacts CRUD -------------------------------------------------------

    # Contacts helpers -------------------------------------------------------

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
        self.contacts_tree.set_rows(tree_rows, iids=[str(r["id"]) for r in rows])

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

    # Client credentials CRUD ------------------------------------------------

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
        self.client_cred_tree.set_rows(tree_rows, iids=[str(r["id"]) for r in rows])

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
        self.office_cred_tree.set_rows(tree_rows, iids=[str(r["id"]) for r in rows])

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

    # Notebook CRUD ---------------------------------------------------------

    def _refresh_notes(self) -> None:
        if "Notebook" not in self._lazy_tabs:
            return
        type_label = self.note_type_menu.get()
        entry_type = None if type_label == "All" else self._notebook_type_key(type_label)
        rows = self.app.db.list_notebook_entries(
            query=self.note_search_var.get(),
            entry_type=entry_type,
            from_date=self._note_from_date,
            to_date=self._note_to_date,
        )
        tree_rows = [
            (
                row.get("entry_date") or "",
                self._notebook_type_label(row.get("entry_type") or "general"),
                row.get("title") or "",
                row.get("author") or "",
                row.get("client_name") or "",
            )
            for row in rows
        ]
        self.notes_tree.set_rows(tree_rows, iids=[str(r["id"]) for r in rows])

    def _filter_notes_today(self) -> None:
        today = date.today().isoformat()
        self._note_from_date = today
        self._note_to_date = today
        self._refresh_notes()

    def _filter_notes_week(self) -> None:
        today = date.today()
        start = today - timedelta(days=today.weekday())
        self._note_from_date = start.isoformat()
        self._note_to_date = today.isoformat()
        self._refresh_notes()

    def _on_note_select(self, iid: str | None) -> None:
        if not iid:
            return
        self._selected_note_id = int(iid)
        row = self.app.db.get_notebook_entry(self._selected_note_id)
        if not row:
            return
        self.n_type.set(self._notebook_type_label(row.get("entry_type") or "general"))
        self.n_title.set(row.get("title") or "")
        self.n_date.set(row.get("entry_date") or "")
        self.n_author.set(row.get("author") or "")
        self.n_client.set(row.get("client_name") or "")
        self.n_follow.set(row.get("follow_up_date") or "")
        self.n_pinned.set(bool(row.get("is_pinned")))
        self.n_body_box.delete("1.0", "end")
        self.n_body_box.insert("1.0", row.get("body") or "")

    def _new_note(self) -> None:
        self._selected_note_id = None
        self._note_from_date = None
        self._note_to_date = None
        self.n_type.set(NOTEBOOK_ENTRY_TYPES[0][1])
        self.n_title.set("")
        self.n_date.set(date.today().isoformat())
        self.n_author.set("")
        self.n_client.set("")
        self.n_follow.set("")
        self.n_pinned.set(False)
        self.n_body_box.delete("1.0", "end")

    def _save_note(self) -> None:
        type_key = self._notebook_type_key(self.n_type.get()) or "general"
        payload = {
            "entry_type": type_key,
            "title": self.n_title.get(),
            "body": self.n_body_box.get("1.0", "end").strip() or None,
            "entry_date": self.n_date.get().strip() or date.today().isoformat(),
            "author": self.n_author.get().strip() or None,
            "client_id": self._client_id(self.n_client.get()),
            "follow_up_date": self.n_follow.get().strip() or None,
            "is_pinned": self.n_pinned.get(),
        }
        try:
            if self._selected_note_id is None:
                self._selected_note_id = self.app.db.add_notebook_entry(**payload)
            else:
                self.app.db.update_notebook_entry(self._selected_note_id, **payload)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Notebook entry saved.")
        self._refresh_notes()

    def _delete_note(self) -> None:
        if self._selected_note_id is None:
            self.feedback.error("Select a note first.")
            return
        if not messagebox.askyesno("Delete note", "Delete this notebook entry?", parent=self.winfo_toplevel()):
            return
        self.app.db.delete_notebook_entry(self._selected_note_id)
        self._new_note()
        self.feedback.success("Note deleted.")
        self._refresh_notes()
