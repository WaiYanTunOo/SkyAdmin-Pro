"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).


class CompanyDetailsPanelMixin0:
    """Per-company overview: services, documents, tax IDs, filing statuses, VO and CSH.
    MRO (method resolution order) matters: mixins are searched left to right,
    so GeneralTabMixin wins over later mixins on name clashes. Order mirrors
    the sub-tab bar: General → Tax IDs → Filing Statuses →
    VO & CSH → Financial Docs → CTkFrame. Keep this order when
    adding tabs; put shared refresh dispatch on this class, never in mixins.
    """
