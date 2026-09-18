from __future__ import annotations

from .tree_fit import fit_tree


class DashboardViewMixin17:
    def _DashboardView_refresh_detail_trees_p2(self, overdue, supplier_due):
        self._fill_money_tree(
            self.overdue_tree,
            overdue,
            lambda item: (
                item.get("client_name") or "—",
                item.get("document_type") or "—",
                item.get("amount") or "—",
                item.get("payment_date") or "—",
            ),
            "No overdue payments.",
        )
        self._fill_money_tree(
            self.supplier_due_tree,
            supplier_due,
            lambda item: (
                item.get("supplier_name") or "—",
                item.get("client_name") or "—",
                item.get("amount") or "—",
                item.get("due_date") or "—",
            ),
            "No supplier payments due.",
        )

    def _fill_money_tree(self, tree, items, row_for, empty_message: str) -> None:
        if items:
            tree.set_rows(
                [row_for(item) for item in items],
                iids=[str(item["id"]) for item in items],
                tags=[("urgent",)] * len(items),
            )
        else:
            tree.set_rows([], empty_message=empty_message)
        fit_tree(tree, len(items or []), empty=1, cap=4)

    def _DashboardView_refresh_detail_trees_p3(self):
        self._detail_scroll._on_content_configure()
