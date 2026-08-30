"""PBKDF2 key material for encrypted databases and ``.skybackup`` archives.

This is separate from license signing (Ed25519 public key in ``license_public.py``).
The material must remain stable so existing encrypted files can be decrypted.
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

_SECRET: bytes | None = None
_SECRET_LOCK = threading.Lock()


def _derive_secret() -> bytes:
    """Derive stable PBKDF2 input for file/backup encryption."""
    global _SECRET
    if _SECRET is not None:
        return _SECRET
    with _SECRET_LOCK:
        if _SECRET is not None:
            return _SECRET

        import binascii as _binascii

        crc_data = repr(_XF).encode() + repr(_XK).encode()
        expected_crc = 0x868E28D8
        actual_crc = _binascii.crc32(crc_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
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
