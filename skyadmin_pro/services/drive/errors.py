"""Drive storage errors."""

from __future__ import annotations

from skyadmin_pro.services.storage_backend import NotConfiguredError

__all__ = ["DriveApiError", "NotConfiguredError"]


class DriveApiError(RuntimeError):
    """Raised when a Drive HTTP call fails."""
