from __future__ import annotations

from ._const_2 import TAB_CLIENTS, TAB_EXPIRY
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_6 import TAB_VO_CSH_SETUP

# Tab names — single source of truth for tabview / lazy loader / refresh.
# Migrated panels (Tasks, Courier, Tax, Pipeline, Suppliers, Accounting) live
# under sidebar Daily Work / Finance pages only.
TAB_NAMES: tuple[str, ...] = (
    TAB_CLIENTS,
    TAB_EXPIRY,
    TAB_COMPANY,
    TAB_VO_CSH_SETUP,
    TAB_RENEWALS,
)
