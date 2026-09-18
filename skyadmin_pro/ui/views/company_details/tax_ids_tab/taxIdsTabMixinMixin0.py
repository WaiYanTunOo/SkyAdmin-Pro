from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import NAV_OFFICE_HUB
from skyadmin_pro.services.workflow import copy_to_clipboard


class TaxIdsTabMixinMixin0:
    def _build_tax_ids(self, master, tree_master=None) -> ctk.CTkFrame:
        cred_card, frame = self._TaxIdsTabMixin_build_tax_ids_p1(master, tree_master)
        self._TaxIdsTabMixin_build_tax_ids_p2(cred_card)
        self._TaxIdsTabMixin_build_tax_ids_p3(frame)
        return frame

    def _set_cred_password_display(self, password: str = "") -> None:
        self.cred_pw_entry.configure(state="normal")
        self.cred_pw_var.set(password or "—")
        self.cred_pw_entry.configure(state="disabled")

    def _load_client_credentials_display(self, client_id: int | None) -> None:
        self._selected_client_cred_id = None
        self._client_cred_rows = {}
        self._set_cred_password_display()
        if client_id is None:
            self.client_cred_tree.set_rows([], empty_message="Select a client to view portal credentials.")
            return
        rows = self.app.db.list_client_credentials(client_id=client_id)
        tree_rows = []
        iids = []
        for row in rows:
            iid = str(row["id"])
            self._client_cred_rows[iid] = row
            iids.append(iid)
            tree_rows.append(
                (
                    row.get("credential_type") or "",
                    row.get("login_id") or row.get("username") or row.get("registration_number") or "",
                    row.get("portal_url") or "",
                )
            )
        self.client_cred_tree.set_rows(
            tree_rows, iids=iids, empty_message="No portal credentials saved for this client."
        )
        if iids:
            self.client_cred_tree.tree.selection_set(iids[0])
            self.client_cred_tree.tree.focus(iids[0])
            self._on_client_cred_select(iids[0])

    def _on_client_cred_select(self, iid: str | None) -> None:
        if not iid:
            self._selected_client_cred_id = None
            self._set_cred_password_display()
            return
        row = self._client_cred_rows.get(str(iid))
        if not row:
            self._selected_client_cred_id = None
            self._set_cred_password_display()
            return
        self._selected_client_cred_id = int(iid)
        self._set_cred_password_display(row.get("password") or "")

    def _copy_client_cred_password(self) -> None:
        secret = self.cred_pw_var.get().strip()
        if not secret or secret == "—":
            self.feedback.error("No password stored for the selected login.")
            return
        copy_to_clipboard(secret)
        self.feedback.success("Password copied.")

    def _open_office_hub_credentials(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        client = self.app.db.get_client(client_id)
        name = (client or {}).get("name") or ""
        if not name:
            self.feedback.error("Select a company first.")
            return
        cred_type = None
        cred_id = self._selected_client_cred_id
        if cred_id is not None:
            row = self._client_cred_rows.get(str(cred_id))
            cred_type = (row or {}).get("credential_type")
        open_hub = getattr(self.app, "open_office_hub_client_credentials", None)
        if callable(open_hub):
            open_hub(name, credential_type=cred_type, credential_id=cred_id)
        else:
            self.app.show_view(NAV_OFFICE_HUB)
