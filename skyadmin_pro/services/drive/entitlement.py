"""License SKU gates for sync / web / Drive (fail closed when claim is set)."""

from __future__ import annotations

from skyadmin_pro.services.drive.keys import (
    SETTING_DRIVE_FILES_ENABLED,
    SETTING_LICENSE_DRIVE_FILES,
    SETTING_LICENSE_MAX_DEVICES,
    SETTING_LICENSE_ORG_ID,
    SETTING_LICENSE_SYNC,
    SETTING_LICENSE_WEB,
)


def _flag(db, key: str) -> str:
    return (db.get_setting(key) or "").strip()


def _parse_max_devices(raw) -> int | None:
    """Positive int = capped; 0 = unlimited (None for UI); invalid/empty = unknown."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        n = int(text)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return n


def license_allows_drive(db) -> bool:
    """True when Worker-issued SKU has drive_files_enabled."""
    return _flag(db, SETTING_LICENSE_DRIVE_FILES) == "1"


def license_allows_sync(db) -> bool:
    """True unless Worker claim explicitly disables sync (empty = unknown/legacy)."""
    claim = _flag(db, SETTING_LICENSE_SYNC)
    return claim != "0"


def license_allows_web(db) -> bool:
    """True when Worker-issued SKU has web_enabled."""
    return _flag(db, SETTING_LICENSE_WEB) == "1"


def license_max_devices(db) -> int | None:
    """Hard device cap from Worker SKU / claims; None if unset or unlimited."""
    n = _parse_max_devices(_flag(db, SETTING_LICENSE_MAX_DEVICES))
    if n is not None:
        return n
    try:
        from skyadmin_pro.services.license.verify.chunk_2 import _read_license_payload

        payload = _read_license_payload() or {}
    except Exception:
        return None
    for key in ("max_devices", "md"):
        if key in payload:
            n = _parse_max_devices(payload.get(key))
            if n is not None:
                return n
    return None


def license_org_id(db) -> str:
    """Firm org_id from last sync register (empty if unknown)."""
    return _flag(db, SETTING_LICENSE_ORG_ID)


def license_devices_status_fragment(db) -> str | None:
    n = license_max_devices(db)
    return f"Devices: {n} max" if n else None


def drive_preference_on(db) -> bool:
    return _flag(db, SETTING_DRIVE_FILES_ENABLED) == "1"


def drive_connect_unlocked(db) -> bool:
    """UI Connect button enabled only when license SKU allows Drive."""
    return license_allows_drive(db)


def set_license_entitlements(
    db,
    *,
    sync: int = 1,
    web: int = 0,
    drive_files: int = 0,
    max_devices: int | None = None,
    org_id: str | None = None,
) -> None:
    db.set_setting(SETTING_LICENSE_SYNC, "1" if sync else "0")
    db.set_setting(SETTING_LICENSE_WEB, "1" if web else "0")
    db.set_setting(SETTING_LICENSE_DRIVE_FILES, "1" if drive_files else "0")
    if max_devices is not None:
        db.set_setting(SETTING_LICENSE_MAX_DEVICES, str(int(max_devices)))
    if org_id is not None:
        oid = str(org_id).strip()
        if oid:
            db.set_setting(SETTING_LICENSE_ORG_ID, oid)
