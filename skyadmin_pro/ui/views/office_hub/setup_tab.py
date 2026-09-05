"""Office Hub — setup tab."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.services.office_hub_rollout import (
    list_office_setup_rows,
    migrate_legacy_ird_passwords,
    seed_liaison_contacts,
)
from skyadmin_pro.ui.setup_rollout import RolloutAction, SetupRolloutPanel


class SetupTabMixin:
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
