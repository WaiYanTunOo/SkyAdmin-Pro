"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations


class ClientsExpiryPanelMixin4:
    def _selected_client_id(self) -> int | None:
        iid = self.client_tree.selected_iid()
        return int(iid) if iid is not None else None
