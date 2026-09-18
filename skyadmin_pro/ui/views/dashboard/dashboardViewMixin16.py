from __future__ import annotations


class DashboardViewMixin16:
    def _DashboardView_refresh_detail_trees_p1(self, snap):
        self.overdue_tree.apply_theme()
        self.supplier_due_tree.apply_theme()
        return snap["overdue"], snap["supplier_due"]
