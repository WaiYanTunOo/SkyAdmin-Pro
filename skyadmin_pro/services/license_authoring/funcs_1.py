from __future__ import annotations

import base64
import json
import string
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from skyadmin_pro.services.license import get_machine_id
from skyadmin_pro.services.license_public import LICENSE_SIGNATURE_ALGORITHM

from .funcs_0 import _dev_private_key, _ed25519_sig_b64url, hmac_hex


def generate_license(
    machine_id: str | None = None,
    days_valid: int | None = 365,
    *,
    issued_at: str | None = None,
    nonce: str | None = None,
    package_days: int | None = None,
) -> str:
    """Generate a legacy HMAC license (rejected by current clients — tests only)."""
    mid = (machine_id or get_machine_id()).strip().upper()
    exp = None
    if days_valid is not None:
        exp = (
            (datetime.now(timezone.utc) + timedelta(days=days_valid))
            .replace(microsecond=0)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    iat = issued_at or datetime.now().strftime("%Y-%m-%dT%H:%M")
    n = nonce or uuid.uuid4().hex[:12]
    pkg = str(package_days) if package_days is not None else (str(days_valid) if days_valid is not None else "")
    payload = "|".join([mid, exp or "", iat, n, pkg])
    sig = hmac_hex(payload)
    data = {"mid": mid, "exp": exp, "sig": sig, "iat": iat, "n": n, "pkg": pkg}
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def generate_passcode(machine_id: str | None = None, days_valid: int | None = None) -> str:
    """Generate a legacy HMAC passcode (rejected by current clients — tests only)."""
    mid = (machine_id or get_machine_id()).strip().upper()
    if days_valid is not None:
        exp_dt = (datetime.now() + timedelta(days=days_valid)).replace(microsecond=0)
        exp_ts = int(exp_dt.timestamp())
        sig = hmac_hex(f"{mid}:passcode:{exp_ts}")
        num = int(sig[:8], 16) % 100_000_000
        alphabet = string.digits + string.ascii_lowercase
        enc = ""
        value = exp_ts
        if value == 0:
            enc = "0"
        else:
            while value:
                value, remainder = divmod(value, 36)
                enc = alphabet[remainder] + enc
        return f"{num:08d}:{enc}"
    sig = hmac_hex(f"{mid}:passcode")
    num = int(sig[:8], 16) % 100_000_000
    return f"{num:08d}"


def build_control_envelope_v2(plaintext: str, private_key: Ed25519PrivateKey | None = None) -> str:
    """Build SKYCTRL2 envelope for tests."""
    from skyadmin_pro.services.license_public import CONTROL_ENVELOPE_V2_PREFIX

    key = private_key or _dev_private_key()
    sig = _ed25519_sig_b64url(key, plaintext)
    envelope = {
        "v": 2,
        "alg": LICENSE_SIGNATURE_ALGORITHM,
        "sig": sig,
        "payload": base64.urlsafe_b64encode(plaintext.encode()).decode().rstrip("="),
    }
    wrapped = base64.urlsafe_b64encode(json.dumps(envelope).encode()).decode().rstrip("=")
    return CONTROL_ENVELOPE_V2_PREFIX + wrapped
