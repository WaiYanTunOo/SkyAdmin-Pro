from __future__ import annotations

import logging
from pathlib import Path

from skyadmin_pro.services.license._constants import LICENSE_FILENAME
from skyadmin_pro.services.license.machine import live_machine_id as get_machine_id
from skyadmin_pro.services.license_crypto import (
    verify_ed25519_passcode_envelope,
)

from .chunk_1 import _shadow_path
from .chunk_6 import fetch_revocations
from .chunk_9 import read_update_info


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = []
    for chunk in str(version).split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer_version(candidate: str, current: str) -> bool:
    return _version_tuple(candidate) > _version_tuple(current)


def available_update() -> dict | None:
    """Return update info when control list advertises a version newer than this build."""
    from skyadmin_pro.config import APP_VERSION

    info = read_update_info()
    if info and is_newer_version(str(info.get("version") or ""), APP_VERSION):
        return info
    return None


def verify_passcode(code: str, machine_id: str | None = None) -> bool:
    """Check if an Ed25519 ``SKYPASS1:`` passcode is valid for this machine."""
    mid = (machine_id or get_machine_id()).strip().upper()
    ok, _msg, _nonce = verify_ed25519_passcode_envelope(code.strip(), mid)
    return ok


def check_for_updates(timeout: float = 6.0) -> tuple[bool, str, dict | None]:
    """Fetch control list and return (sync_ok, message, update_info_or_none)."""
    ok, msg = fetch_revocations(timeout=timeout)
    return ok, msg, available_update()


def generate_license(*_args: object, **_kwargs: object) -> str:
    """Disabled in the desktop client — licenses are issued by the Worker API."""
    raise RuntimeError(
        "License generation is server-side only. "
        "Use POST /api/generate on the SkyAdmin Worker (owner tools), not the desktop app."
    )


def save_license_file(content: str) -> Path:
    """Persist a license key/passcode + a shadow copy + integrity seal."""
    from skyadmin_pro.paths import app_data_dir

    path = app_data_dir() / LICENSE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = (content or "").strip()
    path.write_text(clean, encoding="utf-8")
    # Integrity seal: HMAC of the license content, stored as a hidden sidecar.
    # Detects manual edits / copied keys without matching seal.
    try:
        from skyadmin_pro.services._protect_core import seal_value

        seal_path = path.parent / ".license.seal"
        seal_path.write_text(seal_value(clean), encoding="utf-8")
    except Exception:
        logging.getLogger(__name__).warning("License seal write failed", exc_info=True)
    try:
        shadow = _shadow_path()
        if shadow is not None:
            shadow.parent.mkdir(parents=True, exist_ok=True)
            shadow.write_text(clean, encoding="utf-8")
    except OSError:
        pass
    try:
        from skyadmin_pro.services.data_sync import rotate_sync_credentials_after_license_change

        rotate_sync_credentials_after_license_change()
    except Exception:
        logging.getLogger(__name__).debug("Sync token rotation skipped after license save", exc_info=True)
    return path
