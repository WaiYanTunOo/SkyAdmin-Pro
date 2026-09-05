"""F1.3 / F1.4 — bulk client ops and grouping panel surface checks."""

from __future__ import annotations

from skyadmin_pro.ui.views.database_tasks.clients_panel import ClientsExpiryPanel


def test_clients_panel_bulk_and_group_methods_exist():
    """Panel exposes multi-select bulk actions and local group management."""
    for name in (
        "_batch_delete",
        "_batch_archive",
        "_batch_set_status",
        "_batch_assign_group",
        "_manage_groups",
        "_open_client_dialog",
    ):
        assert callable(getattr(ClientsExpiryPanel, name, None)), name
