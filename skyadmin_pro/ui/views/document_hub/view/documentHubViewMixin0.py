from __future__ import annotations

from skyadmin_pro.ui.views.document_hub.agent_bundle import AgentBundlePanel
from skyadmin_pro.ui.views.document_hub.archive import ArchivePanel
from skyadmin_pro.ui.views.document_hub.financial import FinancialDocsPanel
from skyadmin_pro.ui.views.document_hub.image_pdf import ImageToPdfPanel
from skyadmin_pro.ui.views.document_hub.portal import PortalUploadPanel
from skyadmin_pro.ui.views.document_hub.renamer import SmartRenamerPanel


class DocumentHubViewMixin0:
    title = "Document Hub"
    subtitle = "Folder tools — rename, convert, and archive files. Not the company file."

    def build(self) -> None:
        self._polling = False
        self._poll_after: str | None = None
        self._lazy_panels: dict[str, object] = {}
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        from skyadmin_pro.ui.views.document_hub import view as view_mod

        self.tabs = view_mod.themed_tabview(self.body, command=self._on_tab_changed)
        self.tabs.grid(row=0, column=0, sticky="nsew")
        tab_names = (
            "Smart Renamer",
            "Image to PDF",
            "Agent Bundle",
            "Portal Upload",
            "Archive & Clean",
            "Financial Docs",
        )
        for name in tab_names:
            self.tabs.add(name)
            tab = self.tabs.tab(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self.renamer = None
        self.converter = None
        self.merger = None
        self.portal = None
        self.archive = None
        self.financial = None

    def _ensure_panel(self, name: str) -> None:
        if name in self._lazy_panels:
            return
        tab = self.tabs.tab(name)
        if name == "Smart Renamer":
            self.renamer = SmartRenamerPanel(tab, self.app)
            self.renamer.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.renamer
        elif name == "Image to PDF":
            self.converter = ImageToPdfPanel(tab, self.app)
            self.converter.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.converter
        elif name == "Agent Bundle":
            self.merger = AgentBundlePanel(tab, self.app)
            self.merger.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.merger
        elif name == "Portal Upload":
            self.portal = PortalUploadPanel(tab, self.app)
            self.portal.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.portal
        elif name == "Archive & Clean":
            self.archive = ArchivePanel(tab, self.app)
            self.archive.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.archive
        elif name == "Financial Docs":
            self.financial = FinancialDocsPanel(tab, self.app)
            self.financial.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            self._lazy_panels[name] = self.financial

    def _current_tab(self) -> str:
        try:
            return self.tabs.get()
        except Exception:
            return "Smart Renamer"

    def _on_tab_changed(self) -> None:
        current = self._current_tab()
        if current:
            self._ensure_panel(current)
        self.refresh_active_tab(current)

    def refresh_active_tab(self, tab_name: str | None = None) -> None:
        """Reload only the selected Document Hub tab."""
        if not hasattr(self, "tabs"):
            return
        if tab_name is None:
            tab_name = self._current_tab()
        self._ensure_panel(tab_name)
        if tab_name == "Smart Renamer" and self.renamer is not None:
            self.renamer.refresh()
        elif tab_name == "Portal Upload" and self.portal is not None:
            self.portal.refresh()
        elif tab_name == "Archive & Clean" and self.archive is not None:
            self.archive.refresh()
        elif tab_name == "Financial Docs" and self.financial is not None:
            self.financial.refresh()

    def refresh_all(self) -> None:
        """Backward-compatible alias — refreshes only the active tab."""
        self.refresh_active_tab()
