from __future__ import annotations

from skyadmin_pro.ui.treeview import ThemedTreeview

from ...funcs_1 import _open_sync_conflicts_dialog_p1


def build_conflict_tree(
    top, db, feedback, filter_var, table_menu, total, summary_lbl, on_cleared, _copy_gid, reload_tail
):
    tree = ThemedTreeview(
        top,
        columns=(
            ("logged", "Logged", 120),
            ("table", "Table", 100),
            ("global_id", "Global ID", 160),
            ("direction", "Dir", 44),
            ("winner", "Winner", 90),
            ("loser", "Loser", 90),
            ("org", "Org", 100),
            ("local", "Local", 100),
            ("remote", "Remote", 100),
        ),
        showheight=16,
        on_double_click=_copy_gid,
        table_id="settings.sync_conflicts",
        db=db,
    )
    tree.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))

    def _selected_table() -> str | None:
        choice = (filter_var.get() or "").strip()
        if not choice or choice == "All tables":
            return None
        return choice

    def _actor(row: dict, key: str, hlc_key: str) -> str:
        raw = (row.get(key) or "").strip()
        if raw:
            return raw
        hlc = (row.get(hlc_key) or "").strip()
        if not hlc or "-" not in hlc:
            return ""
        return hlc.rsplit("-", 1)[-1]

    def _reload() -> None:
        tname = _selected_table()
        rows = db.list_sync_conflicts(limit=500, table_name=tname)
        shown = len(rows)
        if tname:
            summary = f"Showing {shown} merge(s) in {tname} (of {total} total)."
        else:
            summary = (
                f"{total} cross-device merge(s) logged — higher HLC kept."
                if shown >= total
                else f"Showing {shown} of {total} merge(s) — higher HLC kept."
            )
        summary_lbl.configure(
            text=(
                f"{summary} Winner/Loser are device nodes. "
                "Double-click a row to copy Global ID. Clear removes the audit only."
            )
        )
        tree.set_rows(
            [
                (
                    str(row.get("logged_at") or "")[:19],
                    row.get("table_name") or "",
                    row.get("global_id") or "",
                    row.get("direction") or "",
                    _actor(row, "actor_winner", "hlc_winner"),
                    _actor(row, "actor_loser", "hlc_loser"),
                    row.get("org_id") or "",
                    str(row.get("local_updated_at") or "")[:19],
                    str(row.get("remote_updated_at") or "")[:19],
                )
                for row in rows
            ],
            empty_message="No conflicts in this filter.",
        )

    table_menu.configure(command=lambda _choice: _reload())
    _open_sync_conflicts_dialog_p1(top, db, feedback, on_cleared, _reload, _copy_gid)
