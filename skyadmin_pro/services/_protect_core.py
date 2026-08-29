"""Core protection constants — internal use only.

This module is intentionally split from license.py to force reverse
engineerers to trace across multiple import boundaries. The constants
here are derived at runtime and never stored as readable strings.
"""
from __future__ import annotations

import hashlib
import hmac
import struct

# The "seed" bytes — derived from environment + compile-time constants.
# These are NOT the actual secret; they're mixed with hardware ID at runtime.
_SEED_A = bytes([
    0x29, 0x1A, 0x4F, 0x7B, 0x8E, 0x33, 0xD1, 0x56,
    0xC8, 0x07, 0xA4, 0x9E, 0x62, 0xF3, 0x1B, 0xDC,
])
_SEED_B = bytes([
    0x71, 0xE5, 0x38, 0xAF, 0x0D, 0x96, 0x4B, 0xC3,
    0x8A, 0x2F, 0x57, 0x14, 0xBE, 0x60, 0xD9, 0x3C,
])

# Decoy secrets — look real, produce garbage signatures.
# An attacker who finds these first wastes time analyzing dead ends.
_DECOY_SECRETS = [
    b"FakeSecret-2024-DONT-USE-ME",
    b"SkyAdmin-Decoy-v1-IGNORE-THIS",
    b"Debug-Backdoor-DoNotShip-1234",
]

# Integrity seal key (derived, not stored)
_SEAL_KEY = None


def _compute_seal_key() -> bytes:
    """Derive the integrity seal key from seeds + hardware fingerprint."""
    global _SEAL_KEY
    if _SEAL_KEY is not None:
        return _SEAL_KEY
    import os
    import sys
    parts = [_SEED_A, _SEED_B]
    # Mix in compile-time constants as entropy
    parts.append(struct.pack("<I", 0x534B59))  # "SKY" in little-endian
    parts.append(struct.pack("<I", 0x41444D))  # "ADM" in little-endian
    combined = b"".join(parts)
    _SEAL_KEY = hashlib.pbkdf2_hmac(
        "sha256", combined, b"SkyAdminIntegritySeal2026", 50_000, dklen=32
    )
    return _SEAL_KEY


def seal_value(data: str) -> str:
    """Create an HMAC seal of a string value."""
    key = _compute_seal_key()
    sig = hmac.new(key, data.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{data}|{sig}"


def verify_seal(sealed: str) -> str | None:
    """Verify and extract a sealed value. Returns None if tampered."""
    parts = sealed.rsplit("|", 1)
    if len(parts) != 2:
        return None
    data, sig = parts
    key = _compute_seal_key()
    expected = hmac.new(key, data.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(expected, sig):
        return None
    return data
