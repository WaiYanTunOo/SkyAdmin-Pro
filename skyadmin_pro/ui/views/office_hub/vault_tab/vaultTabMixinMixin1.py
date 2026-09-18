from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.config import OFFICE_SYSTEM_TYPES
from skyadmin_pro.services.workflow import copy_to_clipboard


class VaultTabMixinMixin1:
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
        if hasattr(self, "_office_cred_scroll"):
            self._office_cred_scroll._on_content_configure()

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
