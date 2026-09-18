from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CLIENT_CREDENTIAL_TYPES
from skyadmin_pro.ui.widgets import themed_tabview


class VaultTabMixinMixin0:
    def _build_passwords_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        pw_tabs = themed_tabview(parent)
        pw_tabs.grid(row=0, column=0, sticky="nsew", padx=4, pady=8)
        pw_tabs.add("Client DBD / RD")
        pw_tabs.add("Office accounts")
        self._password_subtabs = pw_tabs
        self._build_client_credentials_tab(pw_tabs.tab("Client DBD / RD"))
        self._build_office_credentials_tab(pw_tabs.tab("Office accounts"))

    def _build_client_credentials_tab(self, parent: ctk.CTkFrame) -> None:
        form = self._VaultTabMixin_build_client_credentials__p1(parent)
        self._VaultTabMixin_build_client_credentials__p2(form)

    def _build_office_credentials_tab(self, parent: ctk.CTkFrame) -> None:
        form = self._VaultTabMixin_build_office_credentials__p1(parent)
        self._VaultTabMixin_build_office_credentials__p2(form)

    def _refresh_client_credentials(self) -> None:
        if "Passwords" not in self._lazy_tabs:
            return
        cred_type = self.client_cred_type_menu.get()
        ctype = None if cred_type == "All" else cred_type
        rows = self.app.db.list_client_credentials(query=self.client_cred_search_var.get(), credential_type=ctype)
        tree_rows = [
            (
                row.get("client_name") or "",
                row.get("credential_type") or "",
                row.get("login_id") or row.get("username") or row.get("registration_number") or "",
                row.get("portal_url") or "",
            )
            for row in rows
        ]
        self.client_cred_tree.set_rows(
            tree_rows,
            iids=[str(r["id"]) for r in rows],
            empty_message="No client portal logins match this filter.",
        )
        if hasattr(self, "_client_cred_scroll"):
            self._client_cred_scroll._on_content_configure()

    def _on_client_cred_select(self, iid: str | None) -> None:
        if not iid:
            return
        self._selected_client_cred_id = int(iid)
        row = self.app.db.get_client_credential(self._selected_client_cred_id)
        if not row:
            return
        self.cc_client.set(row.get("client_name") or "")
        self.cc_type.set(row.get("credential_type") or CLIENT_CREDENTIAL_TYPES[0])
        self.cc_login_id.set(row.get("login_id") or row.get("username") or row.get("registration_number") or "")
        self.cc_password.set(row.get("password") or "")
        self.cc_url.set(row.get("portal_url") or "")
        self.cc_favorite.set(bool(row.get("is_favorite")))
        self.cc_notes_box.delete("1.0", "end")
        self.cc_notes_box.insert("1.0", row.get("notes") or "")

    def _new_client_credential(self) -> None:
        self._selected_client_cred_id = None
        self.cc_client.set("")
        self.cc_type.set(CLIENT_CREDENTIAL_TYPES[0])
        self.cc_login_id.set("")
        self.cc_password.set("")
        self.cc_url.set("")
        self.cc_favorite.set(False)
        self.cc_notes_box.delete("1.0", "end")

    def _save_client_credential(self) -> None:
        client_id = self._client_id(self.cc_client.get())
        if client_id is None:
            self.feedback.error("Select a valid client company name.")
            return
        payload = {
            "client_id": client_id,
            "credential_type": self.cc_type.get(),
            "login_id": self.cc_login_id.get().strip() or None,
            "password": self.cc_password.get(),
            "portal_url": self.cc_url.get().strip() or None,
            "notes": self.cc_notes_box.get("1.0", "end").strip() or None,
            "is_favorite": self.cc_favorite.get(),
        }
        if self._selected_client_cred_id is not None and not payload["password"]:
            payload.pop("password", None)
        try:
            if self._selected_client_cred_id is None:
                self._selected_client_cred_id = self.app.db.add_client_credential(**payload)
            else:
                self.app.db.update_client_credential(self._selected_client_cred_id, **payload)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Client credential saved (encrypted).")
        self._refresh_client_credentials()
