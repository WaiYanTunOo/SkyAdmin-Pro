from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.services.workflow import copy_to_clipboard


class ContactsTabMixinMixin1:
    def _save_contact(self) -> None:
        client_name = self.c_client.get().strip()
        client_id = self._client_id(client_name) if client_name else None
        if client_name and client_id is None:
            self.feedback.error("Select a valid linked client from the list, or leave blank.")
            return
        org = self.c_org.get().strip() or None
        dept = self.c_dept.get().strip() or None
        if not org and client_name:
            org = client_name
            self.c_org.set(org)
        self.app.db.ensure_directory_entries(organization=org, department=dept)
        self._refresh_contact_pickers()
        payload = {
            "name": self.c_name.get(),
            "role_title": self.c_role.get().strip() or None,
            "organization": org,
            "department": dept,
            "phone": self.c_phone.get().strip() or None,
            "email": self.c_email.get().strip() or None,
            "line_id": self.c_line.get().strip() or None,
            "category": self.c_category.get(),
            "client_id": client_id,
            "notes": self.c_notes_box.get("1.0", "end").strip() or None,
            "is_favorite": self.c_favorite.get(),
        }
        try:
            if self._selected_contact_id is None:
                self._selected_contact_id = self.app.db.add_office_contact(**payload)
            else:
                self.app.db.update_office_contact(self._selected_contact_id, **payload)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.feedback.success("Contact saved.")
        self._refresh_contacts()

    def _delete_contact(self) -> None:
        if self._selected_contact_id is None:
            self.feedback.error("Select a contact first.")
            return
        if not messagebox.askyesno("Delete contact", "Delete this contact?", parent=self.winfo_toplevel()):
            return
        self.app.db.delete_office_contact(self._selected_contact_id)
        self._new_contact()
        self.feedback.success("Contact deleted.")
        self._refresh_contacts()

    def _copy_contact_phone(self) -> None:
        phone = self.c_phone.get().strip()
        if not phone:
            self.feedback.error("No phone number to copy.")
            return
        copy_to_clipboard(phone)
        self.feedback.success("Phone copied.")
