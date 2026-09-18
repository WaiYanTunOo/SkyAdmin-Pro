from __future__ import annotations


class SuppliersPanelMixin1:
    def refresh_after_directory_change(self) -> None:
        """Refresh directory data and any dependent sub-tab combos."""
        if self.directory:
            self.directory.refresh()
        if self.services:
            self.services.refresh()
        if self.payments:
            self.payments.refresh()
