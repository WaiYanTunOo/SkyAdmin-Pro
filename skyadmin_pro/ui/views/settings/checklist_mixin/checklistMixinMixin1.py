from __future__ import annotations

from tkinter import messagebox

from skyadmin_pro.config import CHECKLIST_TEMPLATES, SERVICE_TYPES


class ChecklistMixinMixin1:
    def _delete_checklist_list(self) -> None:
        name = self.checklist_menu.get().strip()
        if not name:
            self.feedback.error("Select a checklist first.")
            return
        builtin = {template_name for template_name, _ in CHECKLIST_TEMPLATES}
        if name in builtin:
            self.feedback.error(f"“{name}” is a built-in list — edit it instead.")
            return
        if not messagebox.askyesno(
            "Delete checklist",
            f"Delete the checklist “{name}”?\n\nCompanies already seeded keep their items.",
            parent=self.winfo_toplevel(),
        ):
            return
        self.app.db.delete_checklist_template(name)
        self._reload_checklists()
        self.feedback.success(f"Checklist “{name}” deleted.")

    def _reset_checklist(self) -> None:
        name = self.checklist_menu.get().strip()
        if not name:
            self.feedback.error("Select a checklist first.")
            return
        self.app.db.reset_checklist_template(name)
        self._reload_checklists(keep=name)
        self.feedback.success(f"Checklist “{name}” reset to the default items.")

    def _save_services(self) -> None:
        lines = self.services_text.get("1.0", "end").splitlines()
        names = [ln.strip() for ln in lines if ln.strip()]
        try:
            self.app.db.set_service_types(names)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self.on_show()
        self._refresh_service_menus()
        self.feedback.success("Services list saved.")
        self.app.set_status("Services list updated.")

    def _reset_services(self) -> None:
        self.app.db.set_service_types(list(SERVICE_TYPES))
        self.on_show()
        self._refresh_service_menus()
        self.feedback.success("Services reset to the default list.")
        self.app.set_status("Services list reset to defaults.")

    def _refresh_service_menus(self) -> None:
        view = self.app.get_view("database_tasks")
        if view is None:
            return
        view._refresh_service_menus()
