from __future__ import annotations

from tkinter import messagebox


def delete_client_group(self, note, group_var, top, id_map, refresh_menu) -> None:
    old = group_var.get().strip()
    if not old:
        note("Select a group first.")
        return
    if not messagebox.askyesno(
        "Delete group",
        f"Delete group '{old}'? Its clients become ungrouped (not deleted).\n\nGroups are this PC only — not synced.",
        parent=top,
    ):
        return
    try:
        self.app.db.delete_client_group(id_map()[old])
    except Exception as exc:
        note(str(exc))
        return
    refresh_menu("")
    note(f"Deleted: {old}")
    self.refresh()
