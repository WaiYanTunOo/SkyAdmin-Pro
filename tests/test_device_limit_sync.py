"""Desktop handling of Worker max_devices / 403 device-limit."""

from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.request

from skyadmin_pro.config import SETTING_DATA_SYNC_ENABLED
from skyadmin_pro.services import data_sync as sync
from skyadmin_pro.services.data_sync.device_limit import is_device_limit_error
from skyadmin_pro.services.drive.entitlement import set_license_entitlements


def patch_sync(monkeypatch, name, value):
    monkeypatch.setattr(sync, name, value)
    for modname, mod in sys.modules.items():
        if (modname.startswith("skyadmin_pro.services.data_sync.chunk_") or modname.endswith("._common")) and hasattr(
            mod, name
        ):
            monkeypatch.setattr(mod, name, value)


def test_register_surfaces_device_limit_403(monkeypatch, fake_app_dir):
    import skyadmin_pro.config as config
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(config, "API_BASE_URL", "https://worker.test")
    patch_sync(monkeypatch, "_license_code", lambda: "fake-license")

    err_body = json.dumps(
        {
            "ok": False,
            "error": "Device limit reached (2/2). Unregister another device or upgrade max_devices.",
        }
    ).encode()

    def boom(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(err_body))

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    ok, msg = sync.register_sync_device()
    assert ok is False
    assert is_device_limit_error(msg)
    assert "2/2" in msg


def test_sync_data_propagates_register_device_limit(monkeypatch, fake_app_dir, db):
    import skyadmin_pro.config as config
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(config, "API_BASE_URL", "https://worker.test")
    set_license_entitlements(db, sync=1, max_devices=2)
    db.set_setting(SETTING_DATA_SYNC_ENABLED, "1")

    limit_msg = "Device limit reached (2/2). Unregister another device or upgrade max_devices."
    patch_sync(monkeypatch, "ensure_sync_credentials", lambda **_kw: (None, limit_msg))
    patch_sync(monkeypatch, "is_data_sync_enabled", lambda _db: True)

    ok, msg = sync.sync_data(db, timeout=5)
    assert ok is False
    assert "Device limit reached" in msg
