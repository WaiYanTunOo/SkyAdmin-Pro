"""Tasks tab — pending/completed task list and editor."""

from __future__ import annotations

import customtkinter as ctk

from ._const_0 import FORM_PADX, annotations  # noqa: F403
from .taskPanelMixin0 import TaskPanelMixin0
from .taskPanelMixin1 import TaskPanelMixin1
from .taskPanelMixin2 import TaskPanelMixin2
from .taskPanelMixin3 import TaskPanelMixin3
from .taskPanelMixin4 import TaskPanelMixin4
from .taskPanelMixin5 import TaskPanelMixin5


class TaskPanel(
    TaskPanelMixin0, TaskPanelMixin1, TaskPanelMixin2, TaskPanelMixin3, TaskPanelMixin4, TaskPanelMixin5, ctk.CTkFrame
):
    pass
