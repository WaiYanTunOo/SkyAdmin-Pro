from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.services.office_hub_rollout import list_office_setup_rows
from skyadmin_pro.ui.setup_rollout import RolloutAction, SetupRolloutPanel


class SetupTabMixinMixin0:
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
        self._ensure_panel("Contacts")
        self.tabs.set("Contacts")
        self.contact_search_var.set(name)
        self._refresh_contacts()
