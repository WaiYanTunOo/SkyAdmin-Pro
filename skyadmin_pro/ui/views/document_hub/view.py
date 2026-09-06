"""Document Hub shell view."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skyadmin_pro.ui.widgets import FeedbackLabel

from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.views.document_hub.agent_bundle import AgentBundlePanel
from skyadmin_pro.ui.views.document_hub.archive import ArchivePanel
from skyadmin_pro.ui.views.document_hub.financial import FinancialDocsPanel
from skyadmin_pro.ui.views.document_hub.image_pdf import ImageToPdfPanel
from skyadmin_pro.ui.views.document_hub.portal import PortalUploadPanel
from skyadmin_pro.ui.views.document_hub.renamer import SmartRenamerPanel
from skyadmin_pro.ui.widgets import themed_tabview


class DocumentHubView(BaseView):
    title = "Document Hub"
    subtitle = "Rename, convert, merge, and archive client documents."

    def build(self) -> None:
        self._polling = False
        self._poll_after: str | None = None
        self._lazy_panels: dict[str, object] = {}
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.tabs = themed_tabview(self.body, command=self._on_tab_changed)
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

    def on_show(self) -> None:
        self._polling = True
        # Cancel any previously scheduled poll chain so re-selecting the view
        # cannot stack multiple concurrent polling loops.
        self._cancel_poll()
        current = self._current_tab()
        if current:
            self._ensure_panel(current)
        self.refresh_active_tab(current)
        self._poll()

    def on_hide(self) -> None:
        self._polling = False
        self._cancel_poll()
        try:
            from skyadmin_pro.ui.async_ui import cancel_pump

            cancel_pump(self)
        except Exception:
            pass

    def _cancel_poll(self) -> None:
        if self._poll_after is not None:
            try:
                self.after_cancel(self._poll_after)
            except Exception:
                pass
            self._poll_after = None

    def _active_feedback(self) -> FeedbackLabel | None:
        current = self._current_tab()
        panel = self._lazy_panels.get(current)
        if panel is not None and hasattr(panel, "feedback"):
            return panel.feedback
        return None

    def _poll(self) -> None:
        if not self._polling or not self.winfo_exists():
            return
        try:
            current = self._current_tab()
            if current == "Smart Renamer" and self.renamer is not None:
                self._poll_folder(
                    self.app.paths.staging,
                    known=lambda: self.renamer.file_list._signature,
                    apply=self._apply_renamer_files,
                )
            elif current == "Portal Upload" and self.portal is not None:
                self._poll_folder(
                    self.app.paths.ready_to_upload,
                    known=lambda: self.portal._signature,
                    apply=self._apply_portal_files,
                )
            elif current == "Archive & Clean" and self.archive is not None:
                self._poll_archive_counts()
        except Exception as exc:
            feedback = self._active_feedback()
            if feedback is not None:
                feedback.error(f"Document Hub refresh failed: {exc}")
        if self._polling and self.winfo_exists():
            self._poll_after = self.after(3000, self._poll)

    def _poll_folder(self, folder, *, known, apply) -> None:
        """Scan one folder off the main thread; apply rows on it only."""
        from skyadmin_pro.services import file_ops
        from skyadmin_pro.ui.async_ui import run_background

        try:
            known_sig = known()
        except Exception:
            known_sig = None

        def work():
            return file_ops.list_files_with_signature(folder)

        def on_success(result) -> None:
            if not self._polling or not self.winfo_exists():
                return
            try:
                files, signature = result
            except Exception:
                return
            if signature == known_sig:
                return
            try:
                apply(files, signature)
            except Exception:
                pass

        run_background(self, work=work, on_success=on_success)

    def _poll_archive_counts(self) -> None:
        """Scan both archive folders off the main thread."""
        from skyadmin_pro.services import file_ops
        from skyadmin_pro.ui.async_ui import run_background

        panel = self.archive
        try:
            known_sig = panel._archive_signature
        except Exception:
            known_sig = None
        ready_folder = self.app.paths.ready_to_upload
        staging_folder = self.app.paths.staging

        def work():
            ready, ready_sig = file_ops.list_files_with_signature(ready_folder)
            staging, staging_sig = file_ops.list_files_with_signature(staging_folder)
            return ready, ready_sig, staging, staging_sig

        def on_success(result) -> None:
            if not self._polling or not self.winfo_exists():
                return
            try:
                ready, ready_sig, staging, staging_sig = result
            except Exception:
                return
            if (ready_sig, staging_sig) == known_sig:
                return
            try:
                panel.render_counts(ready, ready_sig, staging, staging_sig)
            except Exception:
                pass

        run_background(self, work=work, on_success=on_success)

    def _apply_renamer_files(self, files, signature) -> None:
        panel = self.renamer
        if panel is None:
            return
        panel.file_list.set_files(files, signature=signature)
        panel._update_preview()

    def _apply_portal_files(self, files, signature) -> None:
        panel = self.portal
        if panel is None:
            return
        panel.render_files(files, signature)

    def mark_stale(self) -> None:
        """Force next refresh to reload even if signature unchanged."""
        for panel in self._lazy_panels.values():
            if hasattr(panel, "_signature"):
                try:
                    panel._signature = None  # type: ignore[attr-defined]
                except Exception:
                    pass
