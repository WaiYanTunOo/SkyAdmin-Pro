from __future__ import annotations

from skyadmin_pro.config import NAV_COURIER, NAV_PIPELINE, NAV_TASKS

from .visible_cols import add_visible_sheet_fields
from .visible_financial import collect_financial_visible
from .visible_suppliers import collect_supplier_visible


class DatabaseTasksViewMixin5:
    def _DatabaseTasksView_visible_sheet_columns_p3(
        self, fields, id_map, result, sheet, suppliers, tree, tree_attr, visible
    ):
        """Pull visible columns from sidebar-hosted panels (Tasks, Courier, …)."""
        app = getattr(self, "app", None)
        ensure = getattr(app, "_ensure_view", None) if app is not None else None
        if not callable(ensure):
            return
        self._visible_from_daily(result, ensure)
        collect_supplier_visible(result, ensure)
        collect_financial_visible(result, ensure)

    def _visible_from_daily(self, result: dict, ensure) -> None:
        tasks = ensure(NAV_TASKS)
        panel = getattr(tasks, "panel", None)
        add_visible_sheet_fields(
            result,
            "Tasks",
            getattr(panel, "tree", None),
            {
                "client": "client_name",
                "title": "title",
                "category": "category",
                "status": "status",
                "due": "due_date",
                "completed": "completed_at",
            },
        )
        courier = ensure(NAV_COURIER)
        panel = getattr(courier, "panel", None)
        add_visible_sheet_fields(
            result,
            "Courier",
            getattr(panel, "tree", None),
            {
                "sent": "date_sent",
                "client": "client_name",
                "tracking": "tracking_number",
                "driver": "driver_name",
                "destination": "destination",
                "task": "task_title",
            },
        )
        pipe = ensure(NAV_PIPELINE)
        panel = getattr(pipe, "panel", None)
        add_visible_sheet_fields(
            result,
            "Pipeline",
            getattr(panel, "pipe_tree", None),
            {
                "client": "client_name",
                "service": "service",
                "step": "step",
                "status": "status",
            },
        )
