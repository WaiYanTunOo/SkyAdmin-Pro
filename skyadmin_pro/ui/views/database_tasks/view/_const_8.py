from __future__ import annotations

from ._const_2 import TAB_CLIENTS
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS

# Work boards live on the main menu. This section is the company file only.
TAB_NAMES: tuple[str, ...] = (
    TAB_CLIENTS,
    TAB_COMPANY,
    TAB_RENEWALS,
)
