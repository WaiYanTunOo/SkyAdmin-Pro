from __future__ import annotations


class DashboardViewMixin17:
    def _DashboardView_refresh_detail_trees_p2(self, overdue, supplier_due):
        # Orphaned: money trees removed; jump buttons on Today cards remain.
        return

    def _fill_money_tree(self, tree, items, row_for, empty_message: str) -> None:
        return

    def _DashboardView_refresh_detail_trees_p3(self):
        scroll = getattr(self, "_detail_scroll", None)
        if scroll is not None:
            scroll._on_content_configure()
