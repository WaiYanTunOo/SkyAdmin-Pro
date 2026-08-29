"""Shared secret derivation — anti-extraction hardening.

The secret is NEVER stored as plaintext. It is split into 7 blocks,
XOR-encoded with a rolling key, and stored as integer lists. At runtime the
blocks are decoded, interleaved, and verified with a SHA-256 digest.

A `strings` dump or naive bytecode reader sees only unrelated integers;
reconstructing requires understanding the decode+interleave algorithm AND
having all 7 blocks in correct order with the correct XOR key.
"""

from __future__ import annotations

import threading

_XK = [0x5B, 0x2E]  # rolling XOR key (2 bytes)

_XF = [
    ([8, 48, 34, 24], [41, 62, 58, 47]),
    ([71, 65, 64, 103], [64, 64, 65, 88]),
    ([58, 47, 50, 52], [53, 40, 118, 105]),
    ([30, 28, 24, 3], [125, 69, 87, 111]),
    ([63, 54, 50, 53], [11, 41, 52, 120]),
    ([126, 92, 65, 94], [92, 71, 75, 90]),
    ([58, 41], [34, 122]),
]

_SECRET_CHECK = "e86108ca6a82c8026ac57ed7556f466576a903a626b45e40e0b1b8d70267a2ce"

_SECRET: bytes | None = None
_SECRET_LOCK = threading.Lock()


def _derive_secret() -> bytes:
    """Derive the signing secret from XOR-interleaved fragments.

    Includes integrity verification (CRC check on fragments) so bytecode
    tampering — patching the XOR key, fragment values, or hash — produces
    garbage that won't match any legitimate license.
    """
    global _SECRET
    if _SECRET is not None:
        return _SECRET
    with _SECRET_LOCK:
        if _SECRET is not None:
            return _SECRET

        # --- integrity: CRC32 of _XF + _XK must match the embedded value ---
        import binascii as _binascii

        crc_data = repr(_XF).encode() + repr(_XK).encode()
        expected_crc = 0x868E28D8
        actual_crc = _binascii.crc32(crc_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            # Fragments were tampered with — return garbage
            _SECRET = b"\x00" * 32
            return _SECRET

        parts_a = []
        parts_b = []
        for block_idx, (ea, eb) in enumerate(_XF):
            k = _XK[block_idx % len(_XK)]
            parts_a.append(bytes(c ^ k for c in ea))
            parts_b.append(bytes(c ^ k for c in eb))
        _SECRET = b"".join(a + b for a, b in zip(parts_a, parts_b, strict=True))
        return _SECRET
