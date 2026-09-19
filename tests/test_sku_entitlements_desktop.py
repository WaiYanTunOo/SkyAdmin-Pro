"""SKU entitlement gates for sync / web / Drive on desktop."""

from __future__ import annotations

from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED, SETTING_SYNC_AUTO_INTERVAL
from skyadmin_pro.services.data_sync import is_data_sync_enabled
from skyadmin_pro.services.data_sync.device_limit import (
    format_register_http_error,
    is_device_limit_error,
)
from skyadmin_pro.services.data_sync.entitlements import apply_sku_flags_from_response
from skyadmin_pro.services.drive.entitlement import (
    license_allows_sync,
    license_allows_web,
    license_devices_status_fragment,
    license_max_devices,
    set_license_entitlements,
)


class _MemDb:
    def __init__(self):
        self._s: dict[str, str] = {}

    def get_setting(self, key, default=""):
        return self._s.get(key, default)

    def set_setting(self, key, value):
        self._s[key] = str(value)


def test_sync_pref_requires_license_when_claim_zero():
    db = _MemDb()
    db.set_setting(SETTING_DATA_SYNC_ENABLED, "1")
    assert license_allows_sync(db) is True  # no claim yet
    assert is_data_sync_enabled(db) is True
    set_license_entitlements(db, sync=0, web=0, drive_files=0)
    assert license_allows_sync(db) is False
    assert is_data_sync_enabled(db) is False


def test_sync_on_when_sku_allows():
    db = _MemDb()
    db.set_setting(SETTING_DATA_SYNC_ENABLED, "1")
    set_license_entitlements(db, sync=1, web=1, drive_files=0)
    assert is_data_sync_enabled(db) is True
    assert license_allows_web(db) is True


def test_sync_off_when_user_pref_off():
    db = _MemDb()
    set_license_entitlements(db, sync=1)
    db.set_setting(SETTING_DATA_SYNC_ENABLED, "0")
    assert is_data_sync_enabled(db) is False


def test_apply_sku_flags_auto_offs_sync_pref():
    db = _MemDb()
    db.set_setting(SETTING_DATA_SYNC_ENABLED, "1")
    db.set_setting(SETTING_SYNC_AUTO_INTERVAL, "30")
    apply_sku_flags_from_response(db, {"sync_enabled": 0, "web_enabled": 0, "drive_files_enabled": 0})
    assert license_allows_sync(db) is False
    assert db.get_setting(SETTING_DATA_SYNC_ENABLED) == "0"
    assert db.get_setting(SETTING_SYNC_AUTO_INTERVAL) == "off"
    assert is_data_sync_enabled(db) is False


def test_apply_sku_flags_stores_max_devices():
    db = _MemDb()
    apply_sku_flags_from_response(
        db,
        {
            "sync_enabled": 1,
            "web_enabled": 0,
            "drive_files_enabled": 0,
            "max_devices": 2,
        },
    )
    assert license_max_devices(db) == 2
    assert license_devices_status_fragment(db) == "Devices: 2 max"


def test_max_devices_zero_means_unlimited_ui():
    db = _MemDb()
    set_license_entitlements(db, sync=1, max_devices=0)
    assert license_max_devices(db) is None
    assert license_devices_status_fragment(db) is None


def test_device_limit_error_detection():
    msg = "Device limit reached (2/2). Unregister another device or upgrade max_devices."
    assert is_device_limit_error(msg) is True
    assert format_register_http_error(403, msg) == msg
    assert "403" in format_register_http_error(403, "")
