"""Audit log viewer — unified view of tax changes and sync conflicts."""

from __future__ import annotations

import customtkinter as ctk

from .auditLogDialogMixin0 import AuditLogDialogMixin0
from .auditLogDialogMixin1 import AuditLogDialogMixin1


class AuditLogDialog(AuditLogDialogMixin0, AuditLogDialogMixin1, ctk.CTkToplevel):
    pass
