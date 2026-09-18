"""Service pipeline tab — 9-step client engagement tracker."""

from __future__ import annotations

import customtkinter as ctk

from .servicePipelinePanelMixin0 import ServicePipelinePanelMixin0
from .servicePipelinePanelMixin1 import ServicePipelinePanelMixin1
from .servicePipelinePanelMixin2 import ServicePipelinePanelMixin2
from .servicePipelinePanelMixin3 import ServicePipelinePanelMixin3
from .servicePipelinePanelMixin4 import ServicePipelinePanelMixin4


class ServicePipelinePanel(
    ServicePipelinePanelMixin0,
    ServicePipelinePanelMixin1,
    ServicePipelinePanelMixin2,
    ServicePipelinePanelMixin3,
    ServicePipelinePanelMixin4,
    ctk.CTkFrame,
):
    pass
