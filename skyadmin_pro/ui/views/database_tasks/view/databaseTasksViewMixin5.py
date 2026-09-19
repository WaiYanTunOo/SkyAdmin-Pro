from __future__ import annotations


class DatabaseTasksViewMixin5:
    def _DatabaseTasksView_visible_sheet_columns_p3(
        self, fields, id_map, result, sheet, suppliers, tree, tree_attr, visible
    ):
        # Suppliers panel is no longer hosted under Companies; keep hook for API stability.
        return
