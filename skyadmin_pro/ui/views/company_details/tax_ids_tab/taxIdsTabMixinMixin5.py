from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.config import CLIENT_CREDENTIAL_TYPES
from skyadmin_pro.ui.views.company_details.constants import SUBTAB_TAX_IDS


class TaxIdsTabMixinMixin5:
    def _clear_client_cred_form(self) -> None:
        self._selected_client_cred_id = None
        self.cred_type_var.set(CLIENT_CREDENTIAL_TYPES[0])
        self.cred_login_var.set("")
        self.cred_pw_var.set("")
        self.cred_url_var.set("")
        self.cred_favorite_var.set(False)
        self.cred_notes_box.delete("1.0", "end")
        if self._cred_pw_visible:
            self._cred_pw_visible = False
            self.cred_pw_entry.configure(show="*")

    def _new_client_cred(self) -> None:
        if self._selected_client_id() is None:
            self.feedback.error("Select a company first.")
            return
        try:
            self.client_cred_tree.tree.selection_remove(self.client_cred_tree.tree.selection())
        except Exception:
            pass
        self._clear_client_cred_form()

    def _save_client_cred(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        payload = {
            "client_id": client_id,
            "credential_type": self.cred_type_var.get(),
            "login_id": self.cred_login_var.get().strip() or None,
            "password": self.cred_pw_var.get(),
            "portal_url": self.cred_url_var.get().strip() or None,
            "notes": self.cred_notes_box.get("1.0", "end").strip() or None,
            "is_favorite": self.cred_favorite_var.get(),
        }
        if self._selected_client_cred_id is not None and not payload["password"]:
            payload.pop("password", None)
        try:
            if self._selected_client_cred_id is None:
                saved_id = self.app.db.add_client_credential(**payload)
            else:
                saved_id = self._selected_client_cred_id
                self.app.db.update_client_credential(saved_id, **payload)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Portal login saved (encrypted).")
        self._refresh_after_mutation(SUBTAB_TAX_IDS)
        iid = str(saved_id)
        if iid in self._client_cred_rows:
            self.client_cred_tree.tree.selection_set(iid)
            self.client_cred_tree.tree.focus(iid)
            self._on_client_cred_select(iid)

    def _delete_client_cred(self) -> None:
        if self._selected_client_cred_id is None:
            self.feedback.error("Select a portal login first.")
            return
        if not messagebox.askyesno("Delete", "Delete this portal login?", parent=self.winfo_toplevel()):
            return
        self.app.db.delete_client_credential(self._selected_client_cred_id)
        self._clear_client_cred_form()
        self.feedback.success("Portal login deleted.")
        self._refresh_after_mutation(SUBTAB_TAX_IDS)
