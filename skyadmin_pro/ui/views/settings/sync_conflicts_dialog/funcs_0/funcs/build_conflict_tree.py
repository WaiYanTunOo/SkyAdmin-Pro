from __future__ import annotations

from skyadmin_pro.ui.treeview import ThemedTreeview

from ...funcs_1 import _open_sync_conflicts_dialog_p1


def build_conflict_tree(
    top, db, feedback, filter_var, table_menu, total, summary_lbl, on_cleared, _copy_gid, reload_tail
):
    tree = ThemedTreeview(
        top,
        columns=(
            ("logged", "Logged", 130),
            ("table", "Table", 110),
            ("global_id", "Global ID", 200),
            ("direction", "Dir", 50),
            ("local", "Local updated", 120),
            ("remote", "Remote updated", 120),
        ),
        showheight=16,
        on_double_click=_copy_gid,
    )
    tree.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))

    def _selected_table() -> str | None:
        choice = (filter_var.get() or "").strip()
        if not choice or choice == "All tables":
            return None
        return choice

    def _reload() -> None:
        tname = _selected_table()
        rows = db.list_sync_conflicts(limit=500, table_name=tname)
        shown = len(rows)
        if tname:
            summary = f"Showing {shown} conflict(s) in {tname} (of {total} total) — local data was kept."
        else:
            summary = (
                f"{total} conflict(s) logged — your local data was kept."
                if shown >= total
                else f"Showing {shown} of {total} conflict(s) — your local data was kept."
            )
        summary_lbl.configure(
            text=(f"{summary} Double-click a row to copy its Global ID. Clear log removes the audit only.")
        )
        tree.set_rows(
            [
                (
                    str(row.get("logged_at") or "")[:19],
                    row.get("table_name") or "",
                    row.get("global_id") or "",
                    row.get("direction") or "",
                    str(row.get("local_updated_at") or "")[:19],
                    str(row.get("remote_updated_at") or "")[:19],
                )
                for row in rows
            ]
        )

    table_menu.configure(command=lambda _choice: _reload())
    _open_sync_conflicts_dialog_p1(top, db, feedback, on_cleared, _reload, _copy_gid)
