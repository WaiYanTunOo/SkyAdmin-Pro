"""Database & Tasks: company list, company file, renewals, and Excel export."""

from __future__ import annotations

from skyadmin_pro.ui.views.base import BaseView

from ._const_2 import TAB_CLIENTS
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_8 import TAB_NAMES
from .databaseTasksViewMixin0 import DatabaseTasksViewMixin0
from .databaseTasksViewMixin1 import DatabaseTasksViewMixin1
from .databaseTasksViewMixin2 import DatabaseTasksViewMixin2
from .databaseTasksViewMixin3 import DatabaseTasksViewMixin3
from .databaseTasksViewMixin4 import DatabaseTasksViewMixin4
from .databaseTasksViewMixin5 import DatabaseTasksViewMixin5
from .funcs import service_menu_panel_key


class DatabaseTasksView(
    DatabaseTasksViewMixin0,
    DatabaseTasksViewMixin1,
    DatabaseTasksViewMixin2,
    DatabaseTasksViewMixin3,
    DatabaseTasksViewMixin4,
    DatabaseTasksViewMixin5,
    BaseView,
):
    pass


__all__ = [
    "TAB_CLIENTS",
    "TAB_COMPANY",
    "TAB_NAMES",
    "TAB_RENEWALS",
    "DatabaseTasksView",
    "service_menu_panel_key",
]
