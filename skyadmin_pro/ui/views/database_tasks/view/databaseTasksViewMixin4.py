from __future__ import annotations


class DatabaseTasksViewMixin4:
    def _DatabaseTasksView_visible_sheet_columns_p1(self):
        # Ensure Companies trees exist so Clients/Documents can follow Columns.
        try:
            from ._const_2 import TAB_CLIENTS, TAB_EXPIRY

            self._ensure_panel(TAB_CLIENTS)
            self._ensure_panel(TAB_EXPIRY)
        except Exception as e:
            import logging

            logging.error(f"UI Error: {e}")
        # (panel attr, tree attr, sheet name, {ui col id: db field})
        # Derived UI cols (status/days) are omitted — Excel has no matching field.
        specs = (
            (
                "clients_panel",
                "client_tree",
                "Clients",
                {"company": "name", "contact": "contact_name", "email": "email", "status": "status"},
            ),
            (
                "expiry_panel",
                "doc_tree",
                "Documents",
                {"client": "client_name", "type": "document_type", "expiry": "expiry_date"},
            ),
        )
        result: dict[str, list[str]] = {}
        return result, specs

    def _DatabaseTasksView_visible_sheet_columns_p2(self, result, specs):
        fields: list[str] = []
        id_map: dict = {}
        sheet = ""
        tree = None
        tree_attr = ""
        visible: list[str] = []
        for panel_attr, tree_attr, sheet, id_map in specs:
            panel = getattr(self, panel_attr, None)
            tree = getattr(panel, tree_attr, None) if panel is not None and tree_attr else None
            if tree is None or not hasattr(tree, "get_visible_columns"):
                continue
            try:
                visible = tree.get_visible_columns()
            except Exception:
                continue
            fields = [id_map[c] for c in visible if c in id_map]
            if fields:
                result[sheet] = fields
        return fields, id_map, sheet, None, tree, tree_attr, visible
