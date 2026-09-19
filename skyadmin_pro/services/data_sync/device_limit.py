"""Worker max_devices / device-limit errors for Settings sync."""

from __future__ import annotations

_DEVICE_LIMIT_MARKERS = (
    "device limit",
    "max_devices",
    "max devices",
    "too many devices",
)


def is_device_limit_error(message: str) -> bool:
    low = (message or "").lower()
    return any(m in low for m in _DEVICE_LIMIT_MARKERS)


def format_register_http_error(status: int, error: str = "") -> str:
    """Surface Worker register JSON error; keep 403 device-limit text intact."""
    err = (error or "").strip()
    if err:
        return err
    if status == 403:
        return "Sync registration refused (HTTP 403)."
    return f"Sync registration failed (HTTP {status})."


def format_sync_http_error(status: int, error: str = "") -> str:
    """Surface Worker sync JSON error (pull/push) including device-limit 403."""
    err = (error or "").strip()
    if err:
        return err
    return f"Sync HTTP {status}"
