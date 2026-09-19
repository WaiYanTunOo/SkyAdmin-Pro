"""Persist Worker SKU flags returned by sync register."""

from __future__ import annotations


def apply_sku_flags_from_response(db, data: dict) -> None:
    if db is None or not isinstance(data, dict):
        return
    from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED, SETTING_SYNC_AUTO_INTERVAL
    from skyadmin_pro.services.drive.entitlement import set_license_entitlements

    sync = int(data.get("sync_enabled") or 0)
    kwargs: dict = {
        "sync": sync,
        "web": int(data.get("web_enabled") or 0),
        "drive_files": int(data.get("drive_files_enabled") or 0),
    }
    oid = str(data.get("org_id") or "").strip()
    if oid:
        kwargs["org_id"] = oid
    if "max_devices" in data and data.get("max_devices") is not None:
        try:
            kwargs["max_devices"] = int(data.get("max_devices"))
        except (TypeError, ValueError):
            pass
    set_license_entitlements(db, **kwargs)
    if sync == 0:
        # Fail closed in Settings: turn off user pref + auto interval.
        db.set_setting(SETTING_DATA_SYNC_ENABLED, "0")
        db.set_setting(SETTING_SYNC_AUTO_INTERVAL, "off")
