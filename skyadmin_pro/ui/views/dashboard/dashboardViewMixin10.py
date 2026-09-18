from __future__ import annotations

from .money_lines import build_money_lines


class DashboardViewMixin10:
    def _DashboardView_build_detail_trees_priori_p1(self):
        build_money_lines(self)
        return None

    def _DashboardView_build_detail_trees_priori_p2(self, split):
        self._detail_scroll._on_content_configure()
