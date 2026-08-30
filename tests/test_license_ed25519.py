"""Ed25519 license and control-list verification (P3 server-side signing)."""

import base64
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from skyadmin_pro.services import license as lic
from skyadmin_pro.services.license_authoring import generate_license as legacy_generate_license
from skyadmin_pro.services.license_crypto import (
    license_payload_string,
    parse_control_envelope_v2,
    verify_ed25519,
)
from skyadmin_pro.services.license_public import CONTROL_ENVELOPE_V2_PREFIX, LICENSE_SIGNATURE_ALGORITHM


@pytest.fixture
def mid():
    return lic.get_machine_id()


@pytest.fixture
def ed25519_keypair():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def _sign_license(private_key: Ed25519PrivateKey, mid: str, days: int = 7) -> str:
    from datetime import datetime, timedelta, timezone

    exp = (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    iat = datetime.now().strftime("%Y-%m-%dT%H:%M")
    nonce = "ed25519test01"
    pkg = str(days)
    payload = license_payload_string(mid, exp, iat, nonce, pkg)
    sig = base64.urlsafe_b64encode(private_key.sign(payload.encode())).decode().rstrip("=")
    data = {
        "mid": mid,
        "exp": exp,
        "sig": sig,
        "iat": iat,
        "n": nonce,
        "pkg": pkg,
        "alg": LICENSE_SIGNATURE_ALGORITHM,
    }
    return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode().rstrip("=")


def test_client_generate_license_disabled(mid):
    with pytest.raises(RuntimeError, match="server-side only"):
        lic.generate_license(mid, 7)


def test_ed25519_license_verifies(mid, ed25519_keypair, monkeypatch):
    private_key, public_key = ed25519_keypair
    monkeypatch.setattr(
        "skyadmin_pro.services.license_crypto.ED25519_PUBLIC_KEY",
        public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
    )
    key = _sign_license(private_key, mid)
    ok, msg, nonce = lic.check_activation_usable(key)
    assert ok, msg
    assert nonce == "ed25519test01"


def test_ed25519_tampered_signature_rejected(mid, ed25519_keypair, monkeypatch):
    private_key, public_key = ed25519_keypair
    monkeypatch.setattr(
        "skyadmin_pro.services.license_crypto.ED25519_PUBLIC_KEY",
        public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
    )
    key = _sign_license(private_key, mid)
    b64 = key + "=" * (-len(key) % 4)
    obj = json.loads(base64.urlsafe_b64decode(b64))
    obj["pkg"] = "999"
    tampered = base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode().rstrip("=")
    ok, msg = lic.verify_key_text(tampered)
    assert not ok
    assert "signature" in msg.lower()


def test_skyctrl2_envelope_parses(ed25519_keypair, monkeypatch):
    private_key, public_key = ed25519_keypair
    monkeypatch.setattr(
        "skyadmin_pro.services.license_crypto.ED25519_PUBLIC_KEY",
        public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
    )
    plaintext = "REVOKE nonce123\nBAN ABCD1234EFGH5678\n"
    sig = base64.urlsafe_b64encode(private_key.sign(plaintext.encode())).decode().rstrip("=")
    envelope = {
        "v": 2,
        "alg": LICENSE_SIGNATURE_ALGORITHM,
        "sig": sig,
        "payload": base64.urlsafe_b64encode(plaintext.encode()).decode().rstrip("="),
    }
    wrapped = CONTROL_ENVELOPE_V2_PREFIX + base64.urlsafe_b64encode(json.dumps(envelope).encode()).decode().rstrip("=")
    parsed, error = parse_control_envelope_v2(wrapped)
    assert error is None
    assert parsed == plaintext


def test_legacy_hmac_rejected_on_client(mid):
    key = legacy_generate_license(mid, days_valid=7, package_days=7)
    ok, msg, _nonce = lic.check_activation_usable(key)
    assert not ok
    assert "retired" in msg.lower()


def test_ed25519_passcode_round_trip(mid):
    from skyadmin_pro.services.license_authoring import generate_ed25519_passcode

    code = generate_ed25519_passcode(mid, days_valid=7)
    ok, msg = lic.verify_key_text(code)
    assert ok, msg


def test_embedded_ed25519_keypair_round_trip(mid):
    """Worker dev key must match license_public.ED25519_PUBLIC_KEY."""
    import base64

    from cryptography.hazmat.primitives import serialization

    priv_b64 = (
        "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1Mv"
        "U0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo="
    )
    private_key = serialization.load_pem_private_key(base64.b64decode(priv_b64), password=None)
    assert isinstance(private_key, Ed25519PrivateKey)
    key = _sign_license(private_key, mid)
    ok, msg, _nonce = lic.check_activation_usable(key)
    assert ok, msg
