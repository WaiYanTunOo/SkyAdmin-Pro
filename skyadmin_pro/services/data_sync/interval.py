"""Parse SETTING_SYNC_AUTO_INTERVAL (off|15|30|60)."""

from __future__ import annotations

SYNC_AUTO_INTERVAL_DEFAULT = "30"
SYNC_AUTO_INTERVAL_VALUES = frozenset({"off", "15", "30", "60"})


def normalize_sync_auto_interval(raw: str | None) -> str:
    """Return a canonical setting value; unknown → default ``30``."""
    value = (raw or "").strip().lower()
    if value in SYNC_AUTO_INTERVAL_VALUES:
        return value
    return SYNC_AUTO_INTERVAL_DEFAULT


def parse_sync_auto_interval_seconds(raw: str | None) -> int | None:
    """Seconds between background pulls, or ``None`` when auto pull is off."""
    value = normalize_sync_auto_interval(raw)
    if value == "off":
        return None
    return int(value)
