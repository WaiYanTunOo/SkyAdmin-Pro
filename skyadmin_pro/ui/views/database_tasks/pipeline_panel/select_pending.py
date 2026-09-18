"""Select a pipeline row after refresh when Dashboard opened that item."""

from __future__ import annotations


def apply_pending_select(panel) -> None:
    item_id = getattr(panel, "_pending_select", None)
    if item_id is None:
        return
    iid = str(item_id)
    tree = panel.pipe_tree.tree
    if not tree.exists(iid):
        return
    tree.selection_set(iid)
    tree.see(iid)
    tree.focus(iid)
    panel._pending_select = None
