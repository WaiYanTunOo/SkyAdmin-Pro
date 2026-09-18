from __future__ import annotations

from .jumps import follow_next, open_company, open_pipeline


class DashboardViewMixin4:
    def _refresh_detail_trees(self, snap: dict, _seq: int | None = None) -> None:
        self._detail_trees_after = None
        if _seq is not None and _seq != getattr(self, "_snap_seq", 0):
            return
        if not self._visible or not self.winfo_exists():
            return
        if not self._detail_built:
            # Finish any remaining progressive stages before populating rows.
            self._build_detail_trees()
        if not self._detail_built:
            return
        if not self._visible:
            return
        seq = int(getattr(self, "_snap_seq", 0))
        self._timeline_after = self.after(120, lambda s=snap, q=seq: self._draw_timeline_deferred(s, _seq=q))

    def _draw_timeline_deferred(self, snap: dict, _seq: int | None = None) -> None:
        self._timeline_after = None
        if _seq is not None and _seq != getattr(self, "_snap_seq", 0):
            return
        if not self._visible or not self.winfo_exists():
            return
        self._draw_timeline(snap)
        self._trees_ready = True

    def _refresh_next_actions(
        self,
        overdue=None,
        supplier_due=None,
        expiring=None,
        supplier_expiring=None,
        pending_tasks=None,
        ongoing=None,
        renewal_due=None,
    ) -> None:
        pass

    def _next_selected(self, iid: str | None) -> None:
        if iid is None:
            return
        target = self._next_targets.get(iid)
        if not target:
            return
        follow_next(self.app, target[0], target[1], iid)

    def _ongoing_selected(self, iid: str | None) -> None:
        if iid is None:
            return
        tree = getattr(self, "ongoing_tree", None)
        if tree is None:
            open_pipeline(self.app)
            return
        values = tree.tree.item(iid, "values")
        if not values or values[0] in ("", "—"):
            return
        open_company(self.app, values[0])

    def _overdue_selected(self) -> int | None:
        iid = self.overdue_tree.selected_iid()
        return int(iid) if iid is not None else None
