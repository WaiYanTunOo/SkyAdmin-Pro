"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_FILING,
    SUBTAB_GENERAL,
    SUBTAB_TAX_IDS,
    SUBTAB_VO_CSH,
)


class CompanyDetailsPanelMixin2:
    def _current_subtab(self) -> str:
        try:
            return self.tabs.get()
        except Exception:
            return SUBTAB_GENERAL

    def _on_shortcut_save(self) -> bool:
        """Ctrl+S: save the primary form for the visible Company Details sub-tab."""
        tab = self._current_subtab()
        self._ensure_panel(tab)
        if tab == SUBTAB_GENERAL:
            if getattr(self, "_editing_service_id", None) is not None:
                self._save_service()
            elif getattr(self, "_editing_doc_id", None) is not None:
                self._save_document()
            else:
                self._save_company_info()
            return True
        if tab == SUBTAB_TAX_IDS:
            self._save_tax_ids()
            return True
        if tab == SUBTAB_FILING:
            self._save_filing_statuses()
            return True
        if tab == SUBTAB_VO_CSH:
            self._save_vo_csh()
            return True
        return False

    def _on_subtab_changed(self) -> None:
        self._cancel_service_edit()
        self._cancel_document_edit()
        self._ensure_panel(self._current_subtab())
        self.refresh()
