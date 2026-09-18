"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).
from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_ACCOUNTING,
    SUBTAB_FILING,
    SUBTAB_FINANCIAL_DOCS,
    SUBTAB_GENERAL,
    SUBTAB_TAX_IDS,
    SUBTAB_VO_CSH,
    SUBTAB_VO_CSH_SETUP,
)


class CompanyDetailsPanelMixin3:
    def _ensure_panel(self, name: str) -> None:
        if name in self._lazy_tabs:
            return
        tab = self.tabs.tab(name)
        if name == SUBTAB_ACCOUNTING:
            # Tree-first tab: no CanvasScrollFrame so the tree owns the wheel.
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            self._accounting_setup_frame = self._build_accounting_setup(tab)
            self._accounting_setup_frame.grid(row=0, column=0, sticky="nsew")
        elif name == SUBTAB_GENERAL:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            general_scroll = CanvasScrollFrame(tab)
            general_scroll.grid(row=0, column=0, sticky="nsew")
            general_scroll.content.grid_columnconfigure(0, weight=1)
            general_scroll.content.grid_rowconfigure(0, weight=1)
            self._company_frame = self._build_company_info(general_scroll.content)
            self._company_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
            self._services_frame = self._build_services(general_scroll.content)
            self._services_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
            self._docs_frame = self._build_documents(general_scroll.content)
            self._docs_frame.grid(row=2, column=0, sticky="nsew")
        elif name == SUBTAB_TAX_IDS:
            # Form scrolls; client cred tree stays fixed outside the canvas.
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_rowconfigure(2, weight=0)
            tax_ids_scroll = CanvasScrollFrame(tab)
            tax_ids_scroll.grid(row=0, column=0, sticky="nsew")
            tax_ids_scroll.content.grid_columnconfigure(0, weight=1)
            self._tax_ids_frame = self._build_tax_ids(tax_ids_scroll.content, tab)
            self._tax_ids_frame.grid(row=0, column=0, sticky="ew")
        elif name == SUBTAB_FILING:
            # Form scrolls; history tree stays outside canvas with expandable band.
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=2)
            tab.grid_rowconfigure(1, weight=1)
            filing_scroll = CanvasScrollFrame(tab)
            filing_scroll.grid(row=0, column=0, sticky="nsew")
            filing_scroll.content.grid_columnconfigure(0, weight=1)
            self._filing_form_frame = self._build_filing_statuses_form(filing_scroll.content)
            self._filing_form_frame.grid(row=0, column=0, sticky="ew")
            self._filing_history_frame = self._build_filing_history(tab)
            self._filing_history_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        elif name == SUBTAB_VO_CSH_SETUP:
            # Tree-first tab: no CanvasScrollFrame so the tree owns the wheel.
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            self._vo_csh_setup_frame = self._build_vo_csh_setup(tab)
            self._vo_csh_setup_frame.grid(row=0, column=0, sticky="nsew")
        elif name == SUBTAB_VO_CSH:
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            vo_scroll = CanvasScrollFrame(tab)
            vo_scroll.grid(row=0, column=0, sticky="nsew")
            vo_scroll.content.grid_columnconfigure(0, weight=1)
            self._vo_frame = self._build_vo_csh(vo_scroll.content)
            self._vo_frame.grid(row=0, column=0, sticky="ew")
        elif name == SUBTAB_FINANCIAL_DOCS:
            # Tree-first tab: no CanvasScrollFrame so the tree owns the wheel.
            fin_tab = self.tabs.tab(SUBTAB_FINANCIAL_DOCS)
            fin_tab.grid_columnconfigure(0, weight=1)
            fin_tab.grid_rowconfigure(0, weight=1)
            self._fin_frame = self._build_financial_docs(fin_tab)
            self._fin_frame.grid(row=0, column=0, sticky="nsew")
        self._lazy_tabs.add(name)

    # --- shared client selection & refresh ---
