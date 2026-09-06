"""Office Hub shell view."""

from __future__ import annotations

from skyadmin_pro.config import NOTEBOOK_ENTRY_TYPES
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.views.office_hub.contacts_tab import ContactsTabMixin
from skyadmin_pro.ui.views.office_hub.notebook_tab import NotebookTabMixin
from skyadmin_pro.ui.views.office_hub.setup_tab import SetupTabMixin
from skyadmin_pro.ui.views.office_hub.vault_tab import VaultTabMixin
from skyadmin_pro.ui.widgets import FeedbackLabel, themed_tabview


class OfficeHubView(SetupTabMixin, ContactsTabMixin, VaultTabMixin, NotebookTabMixin, BaseView):
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
        self.tabs = themed_tabview(self.body, command=self._on_tab_changed)
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

    def on_hide(self) -> None:
        for attr in ("_client_cred_search_scheduler", "_office_cred_search_scheduler"):
            cancel = getattr(getattr(self, attr, None), "cancel", None)
            if callable(cancel):
                try:
                    cancel()
                except Exception:
                    pass

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
