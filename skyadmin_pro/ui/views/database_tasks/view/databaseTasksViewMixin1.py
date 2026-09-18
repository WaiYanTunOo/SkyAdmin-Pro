from __future__ import annotations

from ._const_0 import TAB_TASKS
from ._const_1 import TAB_COURIER
from ._const_2 import TAB_CLIENTS
from ._const_3 import TAB_MONTH
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_6 import TAB_PIPELINE
from ._const_7 import TAB_SUPPLIERS
from .expand_tabs import FILL_TABS, mount_fill_panel
from .tab_hints import tab_hint


class DatabaseTasksViewMixin1:
    def _ensure_panel(self, name: str) -> None:
        if name in self._lazy_panels:
            return
        tab = self.tabs.tab(name)
        if name not in FILL_TABS:
            return
        # Parent on the tab. CanvasScrollFrame only sets width, so panels stay short.
        panel = mount_fill_panel(self, name, tab)
        panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._lazy_panels[name] = panel

    def _on_tab_changed(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = ""
        self._ensure_panel(current)
        label = getattr(self, "_subtitle_label", None)
        if label is not None:
            label.configure(text=tab_hint(current))
        self.refresh_active_tab(current)

    def refresh_active_tab(self, tab_name: str | None = None) -> None:
        """Reload data for the selected tab only (not all eight panels)."""
        if tab_name is None:
            try:
                tab_name = self.tabs.get()
            except Exception:
                tab_name = TAB_CLIENTS
        self._refresh_service_menus(tab_name)
        if tab_name == TAB_TASKS and self.tasks_panel is not None:
            self.tasks_panel.refresh()
        elif tab_name == TAB_COURIER and self.courier_panel is not None:
            self.courier_panel.refresh()
        elif tab_name == TAB_CLIENTS and self.clients_panel is not None:
            self.clients_panel.refresh()
        elif tab_name == TAB_MONTH and self.month_panel is not None:
            self.month_panel.refresh()
        elif tab_name == TAB_COMPANY and self.company_panel is not None:
            self.company_panel.refresh()
        elif tab_name == TAB_RENEWALS and self.renewals_panel is not None:
            self.renewals_panel.refresh()
        elif tab_name == TAB_PIPELINE and self.pipeline_panel is not None:
            self.pipeline_panel.refresh()
        elif tab_name == TAB_SUPPLIERS and self.suppliers_panel is not None:
            self.suppliers_panel.refresh()
