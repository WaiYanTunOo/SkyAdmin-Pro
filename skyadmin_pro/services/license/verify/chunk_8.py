from __future__ import annotations

import uuid

from skyadmin_pro.services.license.machine import live_machine_id as get_machine_id
from skyadmin_pro.services.license_crypto import (
    verify_ed25519_passcode_envelope,
)
from skyadmin_pro.services.license_public import (
    LEGACY_FORMAT_SUNSET_MESSAGE,
    PASSCODE_PREFIX,
)

from .chunk_4 import banned_machines, revoked_passcodes
from .chunk_7 import _verify_parsed_license


def verify_key_text(text: str) -> tuple[bool, str]:
    """Validate a pasted Ed25519 license key or ``SKYPASS1:`` passcode."""
    import time as _time

    _t0 = _time.monotonic()
    _ = uuid.uuid4().hex
    _elapsed = _time.monotonic() - _t0
    if _elapsed > 0.8:
        return False, "Verification failed."

    raw = "".join((text or "").split())
    if not raw:
        return False, "Paste the license key or passcode."

    current_mid = get_machine_id()
    if current_mid in banned_machines():
        return False, "This machine has been blocked by Sky Creation Innovations."

    if raw.startswith(PASSCODE_PREFIX):
        ok, msg, _nonce = verify_ed25519_passcode_envelope(raw, current_mid)
        if not ok:
            return False, msg
        if raw in revoked_passcodes():
            return False, "This passcode has been revoked by Sky Creation Innovations."
        return True, msg

    if raw.isdigit() and len(raw) == 8:
        return False, LEGACY_FORMAT_SUNSET_MESSAGE

    if ":" in raw:
        parts = raw.rsplit(":", 1)
        if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 8:
            return False, LEGACY_FORMAT_SUNSET_MESSAGE

    return _verify_parsed_license(raw, current_mid)
