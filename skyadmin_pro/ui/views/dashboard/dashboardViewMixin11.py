from __future__ import annotations


class DashboardViewMixin11:
    def _DashboardView_build_detail_trees_second_p1(self):
        if getattr(self, "_detail_stage", 0) < 1:
            self._build_detail_trees_priority()
        self._detail_stage = 2
        return None
