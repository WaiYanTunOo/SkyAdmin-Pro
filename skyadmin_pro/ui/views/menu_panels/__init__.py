"""Sidebar pages that host panels formerly buried in Database & Tasks."""

from .accounting_view import AccountingSetupMenuView
from .courier_view import CourierMenuView
from .pipeline_view import PipelineMenuView
from .suppliers_view import SuppliersMenuView
from .tasks_view import TasksMenuView
from .tax_view import TaxStatusMenuView

__all__ = (
    "AccountingSetupMenuView",
    "CourierMenuView",
    "PipelineMenuView",
    "SuppliersMenuView",
    "TasksMenuView",
    "TaxStatusMenuView",
)
