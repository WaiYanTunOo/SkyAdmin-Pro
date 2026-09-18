"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations


class ClientsExpiryPanelMixin7:
    def _save_client_dialog(
        self,
        top,
        client_id: int | None,
        name_var,
        contact_var,
        email_var,
        status_var,
        group_var=None,
        group_map: dict | None = None,
    ) -> None:
        name = name_var.get().strip()
        if not name:
            self.feedback.error("Enter a company name.")
            return
        contact = contact_var.get().strip()
        email = email_var.get().strip()
        status = "active" if status_var.get() == "Active" else "inactive"
        group_name = (group_var.get() if group_var is not None else "(No group)").strip()
        group_id = (group_map or {}).get(group_name)
        clear_group = group_id is None
        try:
            from skyadmin_pro.services.client_commands import AddClientCommand, EditClientCommand

            if client_id is None:
                self._undo.execute(
                    AddClientCommand(
                        self.app.db,
                        name=name,
                        contact=contact,
                        email=email,
                        status=status,
                        group_id=group_id,
                        clear_group=clear_group,
                    )
                )
                view = self.app.get_view("database_tasks")
                if view is not None and getattr(view, "tasks_panel", None) is not None:
                    view.tasks_panel.refresh()
            else:
                self._undo.execute(
                    EditClientCommand(
                        self.app.db,
                        client_id,
                        name=name,
                        contact_name=contact,
                        email=email,
                        status=status,
                        group_id=group_id,
                        clear_group=clear_group,
                    )
                )
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        top.destroy()
        self.feedback.success(f"Client saved: {name}")
        self.refresh()
