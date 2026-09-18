"""Clients & expiry tab — company list, workspace, and document expiry tracking."""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from skyadmin_pro.services.file_ops import open_in_file_manager, parse_flexible_date
from skyadmin_pro.services.tracking import (
    classify_expiry,
    days_until,
    effective_expiry_date,
    expiry_label,
)
from skyadmin_pro.services.workflow import create_client_workspace
from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField, FeedbackLabel, make_modal, themed_entry

from .chunk_0 import ClientsExpiryPanelMixin0
from .chunk_1 import ClientsExpiryPanelMixin1
from .chunk_2 import ClientsExpiryPanelMixin2
from .chunk_3 import ClientsExpiryPanelMixin3
from .chunk_4 import ClientsExpiryPanelMixin4
from .chunk_5 import ClientsExpiryPanelMixin5
from .chunk_6 import ClientsExpiryPanelMixin6
from .chunk_7 import ClientsExpiryPanelMixin7
from .chunk_8 import ClientsExpiryPanelMixin8
from .chunk_9 import ClientsExpiryPanelMixin9
from .chunk_10 import ClientsExpiryPanelMixin10
from .chunk_11 import ClientsExpiryPanelMixin11
from .chunk_12 import ClientsExpiryPanelMixin12


class ClientsExpiryPanel(
    ClientsExpiryPanelMixin0,
    ClientsExpiryPanelMixin1,
    ClientsExpiryPanelMixin2,
    ClientsExpiryPanelMixin3,
    ClientsExpiryPanelMixin4,
    ClientsExpiryPanelMixin5,
    ClientsExpiryPanelMixin6,
    ClientsExpiryPanelMixin7,
    ClientsExpiryPanelMixin8,
    ClientsExpiryPanelMixin9,
    ClientsExpiryPanelMixin10,
    ClientsExpiryPanelMixin11,
    ClientsExpiryPanelMixin12,
    ctk.CTkFrame,
):
    pass
