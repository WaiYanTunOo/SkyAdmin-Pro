from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import CONTACT_CATEGORIES


class ContactsTabMixinMixin0:
    def _build_contacts_tab(self, parent: ctk.CTkFrame) -> None:
        form = self._ContactsTabMixin_build_contacts_tab_p1(parent)
        self._ContactsTabMixin_build_contacts_tab_p2(form)

    def _refresh_contact_pickers(self) -> None:
        if not hasattr(self, "c_org_menu"):
            return
        companies = [""] + self.app.db.list_organizations()
        depts = [""] + self.app.db.list_departments()
        clients = [""] + self.app.db.list_client_names()
        self.c_org_menu.configure(values=companies)
        self.c_dept_menu.configure(values=depts)
        self.c_client_menu.configure(values=clients)

    def _refresh_contacts(self) -> None:
        if "Contacts" not in self._lazy_tabs:
            return
        cat = self.contact_category_menu.get()
        category = None if cat == "All" else cat
        rows = self.app.db.list_office_contacts(query=self.contact_search_var.get(), category=category)
        tree_rows = [
            (
                row.get("name") or "",
                row.get("organization") or "",
                row.get("role_title") or "",
                row.get("phone") or "",
                row.get("category") or "",
            )
            for row in rows
        ]
        self.contacts_tree.set_rows(
            tree_rows,
            iids=[str(r["id"]) for r in rows],
            empty_message="No contacts match this search.",
        )
        if getattr(self, "_contacts_scroll", None):
            self._contacts_scroll._on_content_configure()

    def _on_contact_select(self, iid: str | None) -> None:
        if not iid:
            return
        self._selected_contact_id = int(iid)
        row = self.app.db.get_office_contact(self._selected_contact_id)
        if not row:
            return
        self.c_name.set(row.get("name") or "")
        self.c_role.set(row.get("role_title") or "")
        self.c_org.set(row.get("organization") or "")
        self.c_dept.set(row.get("department") or "")
        self.c_phone.set(row.get("phone") or "")
        self.c_email.set(row.get("email") or "")
        self.c_line.set(row.get("line_id") or "")
        self.c_category.set(row.get("category") or CONTACT_CATEGORIES[0])
        self.c_client.set(row.get("client_name") or "")
        self.c_favorite.set(bool(row.get("is_favorite")))
        self.c_notes_box.delete("1.0", "end")
        self.c_notes_box.insert("1.0", row.get("notes") or "")

    def _new_contact(self) -> None:
        self._selected_contact_id = None
        self.c_name.set("")
        self.c_role.set("")
        self.c_org.set("")
        self.c_dept.set("")
        self.c_phone.set("")
        self.c_email.set("")
        self.c_line.set("")
        self.c_category.set(CONTACT_CATEGORIES[0])
        self.c_client.set("")
        self.c_favorite.set(False)
        self.c_notes_box.delete("1.0", "end")
