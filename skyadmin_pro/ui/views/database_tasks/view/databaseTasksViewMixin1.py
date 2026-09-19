from __future__ import annotations

from skyadmin_pro.ui.views.database_tasks.tab_names import TabName

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
        """Reload data for the selected tab only (not all panels)."""
        if tab_name is None:
            try:
                tab_name = self.tabs.get()
            except Exception:
                tab_name = TabName.CLIENTS.value
        self._refresh_service_menus(tab_name)
        if tab_name == TabName.CLIENTS.value and self.clients_panel is not None:
            self.clients_panel.refresh()
        elif tab_name == TabName.EXPIRY.value and self.expiry_panel is not None:
            self.expiry_panel.refresh()
        elif tab_name == TabName.COMPANY.value and self.company_panel is not None:
            self.company_panel.refresh()
        elif tab_name == TabName.VO_CSH_SETUP.value and self.vo_csh_setup_panel is not None:
            self.vo_csh_setup_panel.refresh()
        elif tab_name == TabName.RENEWALS.value and self.renewals_panel is not None:
            self.renewals_panel.refresh()
