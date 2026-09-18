from __future__ import annotations

import base64
import json
from datetime import datetime

from skyadmin_pro.services.license_public import (
    CONTROL_ENVELOPE_V2_PREFIX,
    LICENSE_SIGNATURE_ALGORITHM,
)


def _b64url_decode(value: str) -> bytes:
    text = (value or "").replace("-", "+").replace("_", "/")
    text += "=" * (-len(text) % 4)
    return base64.b64decode(text.encode("ascii"))


def verify_ed25519(payload: str, signature_b64url: str) -> bool:
    """Return True when *signature_b64url* is a valid Ed25519 signature."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not signature_b64url:
        return False
    try:
        sig = _b64url_decode(signature_b64url)
        from skyadmin_pro.services import license_crypto as crypto_mod

        key = crypto_mod.ED25519_PUBLIC_KEY
        Ed25519PublicKey.from_public_bytes(key).verify(sig, payload.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def license_payload_string(mid: str, exp: str | None, iat: str, nonce: str, pkg: str) -> str:
    """Canonical signed license payload."""
    return "|".join([mid, exp or "", iat, nonce, pkg])


def passcode_payload_string(mid: str, exp: str | None, nonce: str) -> str:
    """Canonical signed passcode payload."""
    return "|".join(["passcode", mid, exp or "", nonce or ""])


def verify_license_signature(
    *,
    mid: str,
    exp: str | None,
    iat: str,
    nonce: str,
    pkg: str,
    signature: str,
    algorithm: str | None,
) -> bool:
    """Verify a license signature (Ed25519-v1 only)."""
    if algorithm != LICENSE_SIGNATURE_ALGORITHM:
        return False
    payload = license_payload_string(mid, exp, iat, nonce, pkg)
    return verify_ed25519(payload, signature)


def parse_control_envelope_v2(text: str) -> tuple[str | None, str | None]:
    """Decode ``SKYCTRL2:`` envelope → (plaintext, error_message)."""
    if not text.startswith(CONTROL_ENVELOPE_V2_PREFIX):
        return None, "Not a SKYCTRL2 envelope."
    try:
        wrapped = text[len(CONTROL_ENVELOPE_V2_PREFIX) :]
        wrapped += "=" * (-len(wrapped) % 4)
        obj = json.loads(base64.urlsafe_b64decode(wrapped.encode()).decode())
        payload_b64 = str(obj.get("payload", "")).replace("-", "+").replace("_", "/")
        payload_b64 += "=" * (-len(payload_b64) % 4)
        plaintext = base64.b64decode(payload_b64).decode("utf-8")
        sig = str(obj.get("sig", ""))
        if str(obj.get("alg", "")) != LICENSE_SIGNATURE_ALGORITHM:
            return None, "Unsupported control-list algorithm."
        if not verify_ed25519(plaintext, sig):
            return None, "Control list signature invalid — refusing to apply (possible tampering)."
        return plaintext, None
    except Exception as exc:
        return None, f"Control list unreadable: {exc}"


def _parse_expiry_iso(exp: str) -> datetime:
    from datetime import datetime

    text = str(exp).strip()
    if text.endswith("Z"):
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt
