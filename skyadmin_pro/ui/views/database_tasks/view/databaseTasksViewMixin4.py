from __future__ import annotations


class DatabaseTasksViewMixin4:
    def _DatabaseTasksView_visible_sheet_columns_p1(self):
        # (panel attr, tree attr, sheet name, {ui col id: db field})
        specs = (
            (
                "clients_panel",
                "client_tree",
                "Clients",
                {"company": "name", "contact": "contact_name", "email": "email", "status": "status"},
            ),
            (
                "clients_panel",
                "doc_tree",
                "Documents",
                {"client": "client_name", "type": "document_type", "expiry": "expiry_date"},
            ),
            (
                "tasks_panel",
                "tree",
                "Tasks",
                {
                    "client": "client_name",
                    "title": "title",
                    "category": "category",
                    "status": "status",
                    "due": "due_date",
                    "completed": "completed_at",
                },
            ),
            (
                "courier_panel",
                "tree",
                "Courier",
                {
                    "sent": "date_sent",
                    "client": "client_name",
                    "tracking": "tracking_number",
                    "driver": "driver_name",
                    "destination": "destination",
                    "task": "task_title",
                },
            ),
            (
                "pipeline_panel",
                "pipe_tree",
                "Pipeline",
                {"client": "client_name", "service": "service", "step": "step", "status": "status"},
            ),
        )
        result: dict[str, list[str]] = {}
        return result, specs

    def _DatabaseTasksView_visible_sheet_columns_p2(self, result, specs):
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
        # Suppliers panel hosts three tab tables — collect whichever tabs exist.
        suppliers = getattr(self, "suppliers_panel", None)
        return fields, id_map, sheet, suppliers, tree, tree_attr, visible
