from __future__ import annotations

from tkinter import filedialog, messagebox

from skyadmin_pro.services.export import default_export_name, export_to_excel

from ._const_0 import TAB_TASKS
from ._const_2 import TAB_CLIENTS
from ._const_4 import TAB_COMPANY


class DatabaseTasksViewMixin3:
    def _export_excel(self) -> None:
        from skyadmin_pro.ui.views.export_filter_dialog import ExportFilterDialog

        def _do_export(*, date_from=None, date_to=None, status=None, visible_only=False):
            target = filedialog.asksaveasfilename(
                parent=self.winfo_toplevel(),
                title="Export database to Excel",
                defaultextension=".xlsx",
                initialfile=default_export_name(),
                initialdir=str(self.app.paths.root),
                filetypes=[("Excel workbook", "*.xlsx")],
            )
            if not target:
                return
            from pathlib import Path

            from skyadmin_pro.ui.async_ui import run_background

            visible = self._visible_sheet_columns() if visible_only else None
            self.feedback.info("Exporting…")

            def work():
                return export_to_excel(
                    self.app.db,
                    Path(target),
                    date_from=date_from,
                    date_to=date_to,
                    status=status,
                    visible_only=visible,
                    offload=True,
                )

            def on_success(path):
                self.feedback.success(f"Exported to {path.name}")
                self.app.set_status(f"Exported database to {path}")

            def on_error(msg: str):
                self.feedback.error(f"Export failed: {msg}")
                messagebox.showerror("Export failed", msg, parent=self.winfo_toplevel())

            run_background(self, work=work, on_success=on_success, on_error=on_error)

        ExportFilterDialog(self.winfo_toplevel(), on_export=_do_export)

    def _visible_sheet_columns(self) -> dict[str, list[str]]:
        """Map export sheet name → visible DB fields (opt-in visible-only export).

        Only sheets whose panel tree is currently built contribute; the rest
        export complete. UI column ids that don't map to DB fields (derived
        values like document status) are ignored.
        """
        result, specs = self._DatabaseTasksView_visible_sheet_columns_p1()
        fields, id_map, sheet, suppliers, tree, tree_attr, visible = self._DatabaseTasksView_visible_sheet_columns_p2(
            result, specs
        )
        self._DatabaseTasksView_visible_sheet_columns_p3(
            fields, id_map, result, sheet, suppliers, tree, tree_attr, visible
        )
        return result

    def _on_shortcut_export(self) -> None:
        self._export_excel()

    def _on_shortcut_new(self) -> None:
        try:
            self.tabs.set(TAB_CLIENTS)
        except Exception:
            pass
        self._ensure_panel(TAB_CLIENTS)
        if self.clients_panel is not None:
            self.clients_panel._open_client_dialog()

    def _on_shortcut_save(self) -> bool:
        """Save the obvious form on the active Database & Tasks tab.

        Returns True when a save was invoked, False when nothing applies.
        """
        try:
            tab = self.tabs.get()
        except Exception:
            return False
        self._ensure_panel(tab)
        if tab == TAB_TASKS and self.tasks_panel is not None:
            self.tasks_panel._save()
            return True
        if tab == TAB_COMPANY and self.company_panel is not None:
            return bool(self.company_panel._on_shortcut_save())
        return False

    def _on_shortcut_undo(self) -> None:
        self._ensure_panel(TAB_CLIENTS)
        if self.clients_panel is not None:
            self.clients_panel._undo_last()
