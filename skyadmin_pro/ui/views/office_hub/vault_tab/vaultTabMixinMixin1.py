from __future__ import annotations

from skyadmin_pro.config import OFFICE_SYSTEM_TYPES
from skyadmin_pro.services.workflow import copy_to_clipboard


class VaultTabMixinMixin1:
    def _open_client_cred_company_details(self) -> None:
        name = (self.cc_client.get() or "").strip()
        if not name:
            name = (self.client_cred_search_var.get() or "").strip()
        if not name:
            self.feedback.error("Select a client login first.")
            return
        from skyadmin_pro.config import NAV_DATABASE_TASKS

        view = self.app._ensure_view(NAV_DATABASE_TASKS)
        if view is not None and hasattr(view, "open_company_tax_ids"):
            view.open_company_tax_ids(name)
        self.app.show_view(NAV_DATABASE_TASKS)

    def _toggle_client_pw(self) -> None:
        if self.cc_pw_entry is None:
            return
        self._client_pw_visible = not self._client_pw_visible
        show = "" if self._client_pw_visible else "*"
        self.cc_pw_entry.configure(state="normal", show=show)
        self.cc_pw_entry.configure(state="disabled")

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
        self._refresh_office_cred_contact_choices()

    def _refresh_office_cred_contact_choices(self) -> None:
        menu = getattr(self, "oc_contact_menu", None)
        if menu is None:
            return
        names = [""] + [
            (row.get("name") or "").strip()
            for row in self.app.db.list_office_contacts()
            if (row.get("name") or "").strip()
        ]
        current = self.oc_contact.get()
        menu.configure(values=names or [""])
        if current in names:
            self.oc_contact.set(current)

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
