from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services.office_hub_rollout import (
    list_office_setup_rows,
    migrate_legacy_ird_passwords,
    seed_liaison_contacts,
)


class SetupTabMixinMixin1:
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
