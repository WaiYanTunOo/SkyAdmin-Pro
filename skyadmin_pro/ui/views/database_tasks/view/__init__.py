"""Database & Tasks: live task table, courier tracker, clients, and Excel export."""

from __future__ import annotations

from skyadmin_pro.ui.views.base import BaseView

from ._const_0 import TAB_TASKS
from ._const_1 import TAB_COURIER
from ._const_2 import TAB_CLIENTS
from ._const_3 import TAB_MONTH
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_6 import TAB_PIPELINE
from ._const_7 import TAB_SUPPLIERS
from ._const_8 import TAB_NAMES
from ._const_9 import TAB_ACCOUNTING
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
    "TAB_ACCOUNTING",
    "TAB_CLIENTS",
    "TAB_COMPANY",
    "TAB_COURIER",
    "TAB_MONTH",
    "TAB_NAMES",
    "TAB_PIPELINE",
    "TAB_RENEWALS",
    "TAB_SUPPLIERS",
    "TAB_TASKS",
    "DatabaseTasksView",
    "service_menu_panel_key",
]
