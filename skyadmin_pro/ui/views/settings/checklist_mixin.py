"""Settings view mixins."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    SERVICE_TYPES,
)
from skyadmin_pro.ui.widgets import themed_entry


class ChecklistMixin:
    def _reload_checklists(self, keep: str | None = None) -> None:
        names = self.app.db.list_checklist_template_names()
        current = keep or self.checklist_menu.get()
        self.checklist_menu.configure(values=names)
        if current in names:
            self.checklist_menu.set(current)
        elif names:
            self.checklist_menu.set(names[0])
        self._load_checklist_items(self.checklist_menu.get())

    def _load_checklist_items(self, name: str) -> None:
        for frame, *_ in self._checklist_rows:
            frame.destroy()
        self._checklist_rows.clear()
        for entry in self.app.db.get_checklist_template_items(name):
            self._add_checklist_row(str(entry.get("item") or ""), str(entry.get("due_days") or 0))
        self._reconfigure_tab_scroll(self.tabs.tab("Business"))

    def _add_checklist_row(self, item: str, days: str) -> None:
        row = ctk.CTkFrame(self.checklist_scroll, fg_color="transparent")
        row.grid_columnconfigure(0, weight=1)
        item_var = ctk.StringVar(value=item)
        days_var = ctk.StringVar(value=days)
        themed_entry(row, textvariable=item_var).grid(row=0, column=0, sticky="ew")
        themed_entry(row, textvariable=days_var, width=90).grid(row=0, column=1, padx=(6, 0))
        ctk.CTkButton(
            row,
            text="✕",
            width=36,
            fg_color="transparent",
            border_width=1,
            command=lambda f=row: self._remove_checklist_row(f),
        ).grid(row=0, column=2, padx=(6, 0))
        row.pack(fill="x", padx=6, pady=3)
        self._checklist_rows.append((row, item_var, days_var))

    def _remove_checklist_row(self, frame: ctk.CTkFrame) -> None:
        for index, (current, *_) in enumerate(self._checklist_rows):
            if current is frame:
                self._checklist_rows.pop(index)
                frame.destroy()
                self._reconfigure_tab_scroll(self.tabs.tab("Business"))
                return

    def _add_checklist_item(self) -> None:
        item = self._new_item_var.get().strip()
        days_raw = self._new_days_var.get().strip() or "0"
        if not item:
            self.feedback.error("Enter the checklist task text.")
            return
        try:
            days = int(days_raw)
        except ValueError:
            self.feedback.error("Days before expiry must be a number.")
            return
        self._add_checklist_row(item, str(days))
        self._new_item_var.set("")
        self._new_days_var.set("")
        self._reconfigure_tab_scroll(self.tabs.tab("Business"))

    def _save_checklist(self) -> None:
        name = self.checklist_menu.get().strip()
        rows: list[tuple[str, int]] = []
        for _, item_var, days_var in self._checklist_rows:
            item = item_var.get().strip()
            if not item:
                continue
            try:
                days = int(days_var.get().strip() or "0")
            except ValueError:
                self.feedback.error(f"Days for “{item[:30]}…” must be a number.")
                return
            rows.append((item, days))
        if not rows:
            self.feedback.error("Add at least one checklist item.")
            return
        try:
            self.app.db.set_checklist_template_items(name, rows)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self._reload_checklists(keep=name)
        self.feedback.success(f"Checklist “{name}” saved.")
        self.app.set_status(f"Renewal checklist “{name}” updated.")
        self._reconfigure_tab_scroll(self.tabs.tab("Business"))

    def _add_checklist_list(self) -> None:
        name = self._new_list_var.get().strip()
        if not name:
            self.feedback.error("Enter a name for the new checklist.")
            return
        try:
            self.app.db.add_checklist_template(name)
        except ValueError as exc:
            self.feedback.error(str(exc))
            return
        self._new_list_var.set("")
        self._reload_checklists(keep=name)
        self.feedback.success(f"Checklist “{name}” added — add items, then Save.")

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
        view.sync_service_menus()
