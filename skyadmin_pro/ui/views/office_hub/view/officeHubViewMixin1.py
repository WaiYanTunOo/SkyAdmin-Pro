from __future__ import annotations

from skyadmin_pro.config import NOTEBOOK_ENTRY_TYPES
from skyadmin_pro.ui.views.office_hub.vault_tab.vaultTabMixinMixin0 import CLIENTS_LOGIN_TAB


class OfficeHubViewMixin1:
    def focus_client_credentials(
        self,
        client_name: str,
        *,
        credential_type: str | None = None,
        credential_id: int | None = None,
    ) -> None:
        """Open Clients Login Data tab for one client (read-only detail)."""
        clean = (client_name or "").strip()
        if not clean:
            return
        self._ensure_panel("Passwords")
        self.tabs.set("Passwords")
        self._password_subtabs.set(CLIENTS_LOGIN_TAB)
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
            self._clear_client_cred_readonly()
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
