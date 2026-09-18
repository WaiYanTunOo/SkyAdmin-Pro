from __future__ import annotations

from skyadmin_pro.ui.views.company_details import CompanyDetailsPanel
from skyadmin_pro.ui.views.company_details.panel import (
    SUBTAB_ACCOUNTING,
    SUBTAB_TAX_IDS,
    SUBTAB_VO_CSH,
    SUBTAB_VO_CSH_SETUP,
)

from ._const_2 import TAB_CLIENTS
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from .funcs import service_menu_panel_key


class DatabaseTasksViewMixin2:
    def _require_company_panel(self) -> CompanyDetailsPanel:
        self._ensure_panel(TAB_COMPANY)
        assert self.company_panel is not None
        return self.company_panel

    def on_show(self) -> None:
        try:
            current = self.tabs.get()
        except Exception:
            current = TAB_CLIENTS
        self._ensure_panel(current)
        self.refresh_active_tab(current)

    def open_company_details(self, client_name: str) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.select_client(client_name)
        self.refresh_active_tab(TAB_COMPANY)

    def open_company_tax_ids(self, client_name: str) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.select_client(client_name)
        panel.tabs.set(SUBTAB_TAX_IDS)
        self.refresh_active_tab(TAB_COMPANY)

    def open_accounting_setup(self) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.tabs.set(SUBTAB_ACCOUNTING)
        self.refresh_active_tab(TAB_COMPANY)

    def open_vo_csh_setup(self) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.tabs.set(SUBTAB_VO_CSH_SETUP)
        self.refresh_active_tab(TAB_COMPANY)

    def open_company_vo_csh(self, client_name: str) -> None:
        self.tabs.set(TAB_COMPANY)
        panel = self._require_company_panel()
        panel.select_client(client_name)
        panel.tabs.set(SUBTAB_VO_CSH)
        self.refresh_active_tab(TAB_COMPANY)

    def open_task(self, task_id: int) -> None:
        from skyadmin_pro.config import NAV_TASKS

        from .funcs import open_menu_view

        open_menu_view(self.app, NAV_TASKS, "open_task", task_id)

    def open_renewal(self, client_name: str) -> None:
        self._ensure_panel(TAB_RENEWALS)
        self.tabs.set(TAB_RENEWALS)
        assert self.renewals_panel is not None
        self.renewals_panel.select_client(client_name)
        self.renewals_panel.refresh()

    def open_pipeline(self) -> None:
        from skyadmin_pro.config import NAV_PIPELINE

        from .funcs import open_menu_view

        open_menu_view(self.app, NAV_PIPELINE, "open_pipeline")

    def refresh_all(self) -> None:
        if not hasattr(self, "tabs"):
            return
        self.refresh_active_tab()

    def _refresh_service_menus(self, tab_name: str | None = None) -> None:
        """Update service-type combobox values on constructed panels.

        When *tab_name* is given only the panel owning that tab's combo is
        refreshed.  When ``None`` all three known panels are refreshed.
        """
        types = self.app.db.list_service_types()
        if tab_name is not None:
            panel_key = service_menu_panel_key(tab_name)
            if panel_key is None:
                return
            panels = [panel_key]
        else:
            panels = ["clients", "company", "pipeline"]
        for key in panels:
            if key == "clients" and self.clients_panel is not None:
                combo = self.clients_panel.expiry_type
                combo.configure(values=types)
                if combo.get() not in types:
                    combo.set(types[0] if types else "")
            elif key == "company" and self.company_panel is not None:
                combo = getattr(self.company_panel, "service_type", None)
                if combo is not None:
                    combo.configure(values=types)
                    if combo.get() not in types:
                        combo.set(types[0] if types else "")
            elif key == "pipeline" and self.pipeline_panel is not None:
                combo = self.pipeline_panel.pipe_service
                combo.configure(values=types)
                if combo.get() not in types:
                    combo.set(types[0] if types else "")
