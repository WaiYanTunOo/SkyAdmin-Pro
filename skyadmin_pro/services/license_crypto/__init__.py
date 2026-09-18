"""License cryptography — Ed25519 verification only (desktop client)."""

from __future__ import annotations

from skyadmin_pro.services.license_public import (
    CONTROL_ENVELOPE_V2_PREFIX,
    ED25519_PUBLIC_KEY,
    LICENSE_SIGNATURE_ALGORITHM,
    PASSCODE_PREFIX,
)

from .funcs_0 import (
    _b64url_decode,
    _parse_expiry_iso,
    license_payload_string,
    parse_control_envelope_v2,
    passcode_payload_string,
    verify_ed25519,
    verify_license_signature,
)
from .funcs_1 import verify_ed25519_passcode_envelope

__all__ = [
    "CONTROL_ENVELOPE_V2_PREFIX",
    "ED25519_PUBLIC_KEY",
    "LICENSE_SIGNATURE_ALGORITHM",
    "PASSCODE_PREFIX",
    "_b64url_decode",
    "_parse_expiry_iso",
    "license_payload_string",
    "parse_control_envelope_v2",
    "passcode_payload_string",
    "verify_ed25519",
    "verify_ed25519_passcode_envelope",
    "verify_license_signature",
]
