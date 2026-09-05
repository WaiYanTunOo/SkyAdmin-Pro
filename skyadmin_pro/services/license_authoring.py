"""License issuance helpers — tests and owner tooling only (not shipped in PyInstaller builds)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import string
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from skyadmin_pro.services._secret import _derive_secret
from skyadmin_pro.services.license import get_machine_id
from skyadmin_pro.services.license_crypto import license_payload_string, passcode_payload_string
from skyadmin_pro.services.license_public import LICENSE_SIGNATURE_ALGORITHM, PASSCODE_PREFIX

_DEV_PRIVATE_KEY_B64 = (
    "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1Mv"
    "U0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo="
)


def hmac_hex(payload: str) -> str:
    """Legacy HMAC-SHA256 (tests simulating pre-P3.1 issuance only)."""
    return hmac.new(_derive_secret(), payload.encode(), hashlib.sha256).hexdigest()


def _hmac(payload: str) -> str:
    return hmac_hex(payload)


def _dev_private_key() -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(base64.b64decode(_DEV_PRIVATE_KEY_B64), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Expected Ed25519 private key")
    return key


def _ed25519_sig_b64url(private_key: Ed25519PrivateKey, payload: str) -> str:
    return base64.urlsafe_b64encode(private_key.sign(payload.encode("utf-8"))).decode().rstrip("=")


def generate_ed25519_license(
    machine_id: str | None = None,
    days_valid: int | None = 365,
    *,
    issued_at: str | None = None,
    nonce: str | None = None,
    package_days: int | None = None,
    private_key: Ed25519PrivateKey | None = None,
) -> str:
    """Issue an Ed25519-signed license key (Worker-compatible format)."""
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
    payload = license_payload_string(mid, exp, iat, n, pkg)
    key = private_key or _dev_private_key()
    data = {
        "mid": mid,
        "exp": exp,
        "sig": _ed25519_sig_b64url(key, payload),
        "iat": iat,
        "n": n,
        "pkg": pkg,
        "alg": LICENSE_SIGNATURE_ALGORITHM,
    }
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def generate_ed25519_passcode(
    machine_id: str | None = None,
    days_valid: int | None = 30,
    *,
    nonce: str | None = None,
    private_key: Ed25519PrivateKey | None = None,
) -> str:
    """Issue an Ed25519-signed SKYPASS1 passcode."""
    mid = (machine_id or get_machine_id()).strip().upper()
    exp = None
    if days_valid is not None:
        exp = (
            (datetime.now(timezone.utc) + timedelta(days=days_valid))
            .replace(microsecond=0)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    n = nonce or uuid.uuid4().hex[:12]
    payload = passcode_payload_string(mid, exp, n)
    key = private_key or _dev_private_key()
    data = {
        "v": 1,
        "alg": LICENSE_SIGNATURE_ALGORITHM,
        "mid": mid,
        "exp": exp,
        "n": n,
        "sig": _ed25519_sig_b64url(key, payload),
    }
    wrapped = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode().rstrip("=")
    return PASSCODE_PREFIX + wrapped


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
