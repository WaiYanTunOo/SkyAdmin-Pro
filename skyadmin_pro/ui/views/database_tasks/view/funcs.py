from __future__ import annotations

from ._const_2 import TAB_CLIENTS
from ._const_4 import TAB_COMPANY
from ._const_6 import TAB_PIPELINE


def open_menu_view(app, key: str, method: str, *args) -> None:
    """Open a main-menu page that used to be a Database & Tasks tab."""
    view = app._ensure_view(key)
    app.show_view(key)
    opener = getattr(view, method, None) if view is not None else None
    if callable(opener):
        opener(*args)


def service_menu_panel_key(tab_name: str) -> str | None:
    """Map Database & Tasks tab to the panel that owns a service-type combo, if any."""
    return {
        TAB_CLIENTS: "clients",
        TAB_COMPANY: "company",
        TAB_PIPELINE: "pipeline",
    }.get(tab_name)
