"""TabName enum — single source of truth for all Database & Tasks tab names.

Existing ``TAB_*`` constants remain as aliases for backward compatibility.
Use ``TabName`` in new code for type-safe comparisons.
"""

from __future__ import annotations

from enum import Enum


class TabName(str, Enum):
    """All top-level Database & Tasks tab names."""

    CLIENTS = "Clients"
    EXPIRY = "Expiry"
    COMPANY = "Company Details"
    VO_CSH_SETUP = "VO/CSH Setup"
    RENEWALS = "Renewals"
    TASKS = "Tasks"
    COURIER = "Courier Tracker"
    MONTH = "Monthly Service Close"
    SUPPLIERS = "Suppliers & AP"


# Backward-compatible module-level constants
TAB_CLIENTS = TabName.CLIENTS.value
TAB_EXPIRY = TabName.EXPIRY.value
TAB_COMPANY = TabName.COMPANY.value
TAB_VO_CSH_SETUP = TabName.VO_CSH_SETUP.value
TAB_RENEWALS = TabName.RENEWALS.value
TAB_TASKS = TabName.TASKS.value
TAB_COURIER = TabName.COURIER.value
TAB_MONTH = TabName.MONTH.value
TAB_SUPPLIERS = TabName.SUPPLIERS.value

TAB_NAMES: tuple[str, ...] = tuple(
    member.value
    for member in (
        TabName.CLIENTS,
        TabName.EXPIRY,
        TabName.COMPANY,
        TabName.VO_CSH_SETUP,
        TabName.RENEWALS,
    )
)
