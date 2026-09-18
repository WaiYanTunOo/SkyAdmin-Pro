from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services.workflow import copy_to_clipboard


class VaultTabMixinMixin2:
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
