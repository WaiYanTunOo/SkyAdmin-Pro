from __future__ import annotations

from datetime import datetime

from .funcs_1 import _format_sync_remaining


def get_daily_sync_status() -> tuple[bool, str]:
    """Return (is_ok, human_message) for UI — time remaining until next check."""
    from skyadmin_pro.services.license import online as online_mod

    last = online_mod._get_last_sync_time()
    if last is None:
        return False, "Connect to internet"
    age = (datetime.now() - last).total_seconds()
    return _format_sync_remaining(age)
