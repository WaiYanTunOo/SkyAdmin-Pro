from __future__ import annotations

from ._const_0 import TAB_TASKS
from ._const_1 import TAB_COURIER
from ._const_2 import TAB_CLIENTS
from ._const_3 import TAB_MONTH
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_6 import TAB_PIPELINE
from ._const_7 import TAB_SUPPLIERS

# Tab names — single source of truth for tabview / lazy loader / refresh.
TAB_NAMES: tuple[str, ...] = (
    TAB_TASKS,
    TAB_COURIER,
    TAB_CLIENTS,
    TAB_MONTH,
    TAB_COMPANY,
    TAB_RENEWALS,
    TAB_PIPELINE,
    TAB_SUPPLIERS,
)
