from __future__ import annotations

import base64
import json
from datetime import datetime

from skyadmin_pro.services.license_public import LICENSE_SIGNATURE_ALGORITHM, PASSCODE_PREFIX

from .funcs_0 import _parse_expiry_iso, passcode_payload_string, verify_ed25519


def verify_ed25519_passcode_envelope(
    raw: str,
    current_mid: str,
) -> tuple[bool, str, str | None]:
    """Validate ``SKYPASS1:`` passcode. Returns (ok, message, nonce)."""

    text = (raw or "").strip()
    if not text.startswith(PASSCODE_PREFIX):
        return False, "Not an Ed25519 passcode.", None
    try:
        wrapped = text[len(PASSCODE_PREFIX) :]
        wrapped += "=" * (-len(wrapped) % 4)
        data = json.loads(base64.urlsafe_b64decode(wrapped.encode()).decode())
        if str(data.get("alg", "")) != LICENSE_SIGNATURE_ALGORITHM:
            return False, "Unsupported passcode algorithm.", None
        mid = str(data.get("mid") or "").strip().upper()
        exp = data.get("exp")
        nonce = str(data.get("n") or "")
        sig = str(data.get("sig") or "")
        if mid != current_mid.strip().upper():
            return False, f"Passcode is for machine {mid}, but this machine is {current_mid}.", None
        payload = passcode_payload_string(mid, str(exp) if exp else None, nonce)
        if not verify_ed25519(payload, sig):
            return (
                False,
                "Passcode signature invalid — issued with a different signing key "
                "or the Worker LICENSE_ED25519_PRIVATE_KEY_B64 does not match this app build.",
                None,
            )
        if exp:
            exp_dt = _parse_expiry_iso(str(exp))
            if datetime.now() >= exp_dt:
                return False, f"Passcode expired on {exp_dt.strftime('%Y-%m-%d %H:%M')}. Request a renewal.", None
            return (
                True,
                f"Passcode accepted for machine {mid} (expires: {exp_dt.strftime('%Y-%m-%d %H:%M')}).",
                nonce or None,
            )
        return True, f"Passcode accepted for machine {mid}.", nonce or None
    except Exception as exc:
        return False, f"Could not read passcode ({exc}).", None
