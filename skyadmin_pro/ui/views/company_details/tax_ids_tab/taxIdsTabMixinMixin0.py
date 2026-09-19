from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.services.workflow import copy_to_clipboard


class TaxIdsTabMixinMixin0:
    def _build_tax_ids(self, master, tree_master=None) -> ctk.CTkFrame:
        tree_card, frame = self._TaxIdsTabMixin_build_tax_ids_p1(master, tree_master)
        self._TaxIdsTabMixin_build_tax_ids_p2(tree_card, frame)
        self._TaxIdsTabMixin_build_tax_ids_p3(frame)
        return frame

    def _toggle_client_cred_pw(self) -> None:
        self._cred_pw_visible = not self._cred_pw_visible
        self.cred_pw_entry.configure(show="" if self._cred_pw_visible else "*")

    def _load_client_credentials_display(self, client_id: int | None) -> None:
        self._client_cred_rows = {}
        self._clear_client_cred_form()
        if client_id is None:
            self.client_cred_tree.set_rows([], empty_message="Select a client to manage portal credentials.")
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
            self._clear_client_cred_form()
            return
        row = self._client_cred_rows.get(str(iid))
        if not row:
            self._clear_client_cred_form()
            return
        self._selected_client_cred_id = int(iid)
        self.cred_type_var.set(row.get("credential_type") or "DBD")
        self.cred_login_var.set(row.get("login_id") or row.get("username") or row.get("registration_number") or "")
        self.cred_pw_var.set(row.get("password") or "")
        self.cred_url_var.set(row.get("portal_url") or "")
        self.cred_favorite_var.set(bool(row.get("is_favorite")))
        self.cred_notes_box.delete("1.0", "end")
        self.cred_notes_box.insert("1.0", row.get("notes") or "")

    def _copy_client_cred_password(self) -> None:
        secret = self.cred_pw_var.get().strip()
        if not secret:
            self.feedback.error("No password stored for the selected login.")
            return
        copy_to_clipboard(secret)
        self.feedback.success("Password copied.")
