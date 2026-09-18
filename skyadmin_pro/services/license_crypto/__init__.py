"""License cryptography — Ed25519 verification only (desktop client)."""

from __future__ import annotations

from .funcs_0 import (  # noqa: F403
    CONTROL_ENVELOPE_V2_PREFIX,
    ED25519_PUBLIC_KEY,
    LICENSE_SIGNATURE_ALGORITHM,
    _b64url_decode,
    _parse_expiry_iso,
    annotations,
    base64,
    datetime,
    json,
    license_payload_string,
    parse_control_envelope_v2,
    passcode_payload_string,
    verify_ed25519,
    verify_license_signature,
)
from .funcs_1 import (  # noqa: F403
    LICENSE_SIGNATURE_ALGORITHM,
    PASSCODE_PREFIX,
    _parse_expiry_iso,
    annotations,
    base64,
    datetime,
    json,
    verify_ed25519,
    verify_ed25519_passcode_envelope,
)
